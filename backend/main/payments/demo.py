"""A payment provider for demos and tests. No money moves.

Test cards (any future expiry date and any CVC):

    4242 4242 4242 4242   payment succeeds
    4000 0000 0000 0002   card declined
    4000 0000 0000 9995   insufficient funds
"""

import re
from datetime import date

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

DECLINED = "4000000000000002"
INSUFFICIENT_FUNDS = "4000000000009995"


def luhn_valid(number):
    digits = [int(d) for d in number]
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def validate_card(number, expiry, cvc, today=None):
    """Return the card number without spaces, or raise ValidationError."""
    number = re.sub(r"[\s-]", "", number or "")
    errors = {}
    if not re.fullmatch(r"\d{13,19}", number) or not luhn_valid(number):
        errors["card_number"] = _("The card number is not valid.")

    match = re.fullmatch(r"\s*(\d{1,2})\s*/\s*(\d{2}|\d{4})\s*", expiry or "")
    if not match or not 1 <= int(match.group(1)) <= 12:
        errors["expiry"] = _("Enter the expiry date as MM/YY.")
    else:
        month, year = int(match.group(1)), int(match.group(2))
        year += 2000 if year < 100 else 0
        today = today or date.today()
        if (year, month) < (today.year, today.month):
            errors["expiry"] = _("The card has expired.")

    if not re.fullmatch(r"\d{3,4}", (cvc or "").strip()):
        errors["cvc"] = _("Enter the 3 or 4 digit security code.")

    if errors:
        raise ValidationError(errors)
    return number


class DemoProvider:
    name = "demo"

    def start(self, payment):
        """Nothing to prepare, the SPA shows its own card form."""
        payment.redirect_url = ""
        payment.save(update_fields=["redirect_url"])

    def charge(self, number):
        """Return None on success or a translated failure reason."""
        if number == DECLINED:
            return _("Your card was declined.")
        if number == INSUFFICIENT_FUNDS:
            return _("Your card has insufficient funds.")
        return None
