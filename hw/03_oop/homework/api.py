
import json
from datetime import datetime
import logging
import hashlib
import uuid

from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from scoring import get_score, get_interests

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field:
    empty_values = (None, '', [], (), {})

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable
        self.is_correct = True
        self.value = None


    def validate(self, value):
        if not value and self.required:
            self.is_correct = False
        if not value and not self.nullable:
            self.is_correct = False
        if self.is_correct:
            self.value = value
    def __str__(self):
        return str(self.value)


class CharField(Field):
    def validate(self, value):
        super().validate(value)

class ArgumentsField(CharField):
    pass


class EmailField(CharField):
    def validate(self, value):
        super().validate(value)
        if '@' not in value:
            self.is_correct = False
        if self.is_correct:
            self.value = value

class PhoneField(CharField):
    def validate(self, value):
        super().validate(value)
        if value and self.is_correct:
            try:
                int(value)
            except ValueError:
                self.is_correct = False
            if not value.startswith("7") or len(value) != 11:
                self.is_correct = False
        if self.is_correct:
            self.value = value



class DateField(CharField):
    def validate(self, value):
        super().validate(value)


class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)
        if value and self.is_correct:
            try:
                value = datetime.strptime(value, "%d.%m.%Y")
            except ValueError:
                raise ValueError("Wrong date format. should be dd-mm-yyyy")
            delta = datetime.today() - value
            if delta.days/365 > 70:
                raise ValueError("Delta should be less than 70 years")
        if self.is_correct:
            self.value = value


class GenderField(CharField):
    def validate(self, value):
        super().validate(value)
        if value and self.is_correct:
            if value not in GENDERS:
                raise ValueError("Wrong value. Should be 0, 1 or 2")
        if self.is_correct:
            self.value = value

class ClientIDsField(Field):
    pass


class Request:
    def __init__(self, data):
        self.data = data

    def validate(self):
        self.errors = []
        for name, field in self.data.items():
            obj_ = getattr(self, name, None)
            obj_.validate(field)
            val_status = obj_.is_correct
            if val_status == False:
                self.errors.append(val_status)
        self.is_valid = False if self.errors else True

class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def get_method(self):
        return self.method.value

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN



class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


    def check_non_empty(self):
        non_empty_lst = []
        for name, field in self.data.items():
            if field:
                non_empty_lst.append(name)
        return non_empty_lst



def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(bytes(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT, "utf-8")).hexdigest()
    else:
        digest = hashlib.sha512(bytes(str(request.account) + str(request.login) + SALT, "utf-8")).hexdigest()
    if digest == str(request.token):
        return True
    return False

class OnlineScoreHandler:
    def process_request(self, request, context, store):
        r = OnlineScoreRequest(request.data['arguments'])
        r.validate()
        if not r.is_valid:
            return r.errors, INVALID_REQUEST
        if request.is_admin:
            score = 42
        else:
            score = get_score(store, r.phone, r.email, r.birthday, r.gender, r.first_name, r.last_name)
        context["has"] = r.check_non_empty()
        return {"score": score}, OK


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)




    def cnt_ids(self):
        return len(self.client_ids.value)



class ClientInterestHandler:
    def process_request(self, request, context, store):
        r = ClientsInterestsRequest(request.data['arguments'])
        r.validate()
        if not r.is_valid:
            return r.errors, INVALID_REQUEST
        context["nclients"] = len(r.client_ids.value)
        response_body = {cid: get_interests(store, cid) for cid in r.client_ids.value}
        return response_body, OK


def method_handler(request, ctx, store):
    handlers = {'online_score': OnlineScoreHandler,
                'clients_interests': ClientInterestHandler}

    method_request = MethodRequest(request["body"])
    method_request.validate()

    if not method_request.is_valid:
        return """Invalid request's fields""", INVALID_REQUEST

    if not check_auth(method_request):
        return ('Forbidden', FORBIDDEN)

    handler = handlers[method_request.get_method]()
    response, code = handler.process_request(method_request, ctx, store)
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(bytes(json.dumps(r), "utf-8"))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()

