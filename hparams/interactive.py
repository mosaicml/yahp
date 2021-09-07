from typing import List


def query_yes_no(
    question: str,
    default: bool = True,
):
    if default is None:
        prompt = " [y/n] "
    elif default:
        prompt = " [Y/n] "
    else:
        prompt = " [y/N] "
    while True:
        choice = input(question + prompt).lower()
        if default is not None and choice == '':
            return default
        if "yes".startswith(choice.lower()):
            return True
        if "no".startswith(choice.lower()):
            return False
        print("Please respond with 'yes' or 'no' " "(or 'y' or 'n').")


def list_options(
    input_text: str,
    options: List[str],
    default_response: str = None,
    allow_custom_response: bool = False,
    multiple_ok: bool = False,
    pre_helptext: str = "Interactive selection...",
    helptext: str = "put a number or enter your own option",
):
    options = [x for x in options if x is not None]
    default_response_pren = "({})".format(default_response) if default_response is not None else ""
    if len(options) <= 1:
        print(f"{ pre_helptext }")
        if len(options) == 1:
            default_response = options[0]
            default_response_pren = "({})".format(default_response)
        response = None
        while response is None:
            response = input("{} {}: ".format(input_text, default_response_pren)) or default_response
            if response is None:
                print(response, "received. Please input a response: ")
        return response
    response = None
    while response is None:
        print(f"\n{ pre_helptext }")
        for count, option in enumerate(options):
            print("{}): {}".format(count + 1, option))
        response = input("{} ({}): ".format(input_text, helptext)).strip()
        try:
            num_response = int(response)
            response = options[num_response - 1]
        except Exception as _:
            if response is None and not multiple_ok:
                print(response, "received. Please input a response: ")
            if response == "" and default_response:
                response = default_response
                break
        if multiple_ok:
            try:
                response_nums = [int(x.strip()) for x in response.split(",")]
                response = [options[x - 1] for x in response_nums]
            except Exception as _:
                if response is None:
                    print(response, "received. Please input a response: ")
        if not allow_custom_response:
            if isinstance(response, list):
                if not all((x in options for x in response)):
                    response = None
            else:
                if response not in options:
                    response = None
    if isinstance(response, list):
        print(f"\nSelected: {', '.join( response )}")
    else:
        print(f"\nSelected: {response}")
    return response
