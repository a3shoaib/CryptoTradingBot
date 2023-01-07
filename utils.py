# Checks if text is a positive integer
def check_integer_format(text: str):
    if text == "":
        # Want the user to be able to delete what they typed
        return True
    if all(x in "0123456789" for x in text):
        try:
            int(text)
            return True
        except ValueError:
            return False

    else:
        return False

# Checks if text is a positive float number
def check_float_format(text: str):
    if text == "":
        # Want the user to be able to delete what they typed
        return True
    # Max of 1 decimal point
    if all(x in "0123456789." for x in text) and text.count(".") <= 1:
        try:
            float(text)
            return True
        except ValueError:
            return False

    else:
        return False

