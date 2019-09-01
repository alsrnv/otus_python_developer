import hashlib
import datetime
import functools
import unittest

import api


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class TestEmailField(unittest.TestCase):

    @cases(['saranov92@gmail.com', 'qq@mail.ru'])
    def test_valid_email_field(self, value):
        self.assertEqual(value, api.EmailField().validate(value))

    @cases(['', 'None', 'qqq'])
    def test_invalid_email_field(self, value):
        with self.assertRaises(ValueError):
            api.EmailField().validate(value)


class TestPhoneField(unittest.TestCase):

    @cases(["79654483454"])
    def test_valid_phone(self, value):
        self.assertEqual(value, api.PhoneField().validate(value))

    @cases(['89919', 'fdfdd'])
    def test_invalid_phone_field(self, value):
        with self.assertRaises(ValueError):
            api.PhoneField().validate(value)

class TestBirthdayField(unittest.TestCase):
    @cases(["19.07.2017"])
    def test_valid_birthday(self, value):
        self.assertEqual(value, api.BirthDayField().validate(value))

    @cases(['89919', 'fdfdd', '2018.01.01'])
    def test_invalid_birthday(self, value):
        with self.assertRaises(ValueError):
            api.BirthDayField().validate(value)

class TestGenderField(unittest.TestCase):
    @cases([1])
    def test_valid_gender(self, value):
        self.assertEqual(value, api.GenderField().validate(value))

    @cases(['89919'])
    def test_invalid_gender(self, value):
        with self.assertRaises(ValueError):
            api.GenderField().validate(value)


if __name__ == "__main__":
    unittest.main()