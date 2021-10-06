from typing import List, Optional


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


def query_singular_option(
    input_text: str,
    options: List[str],
    default_response: Optional[str] = None,
    allow_custom_response: bool = False,
    pre_helptext: str = "Interactive selection...",
    helptext: str = "put a number or enter your own option",
) -> str:
    option = _list_options(
        input_text=input_text,
        options=options,
        default_response=default_response,
        allow_custom_response=allow_custom_response,
        pre_helptext=pre_helptext,
        multiple_ok=False,
        helptext=helptext,
    )
    assert isinstance(option, str)
    return option


def query_multiple_options(
    input_text: str,
    options: List[str],
    default_response: str = None,
    allow_custom_response: bool = False,
    pre_helptext: str = "Interactive selection...",
    helptext: str = "put a number or enter your own option",
) -> List[str]:
    option = _list_options(
        input_text=input_text,
        options=options,
        default_response=default_response,
        allow_custom_response=allow_custom_response,
        pre_helptext=pre_helptext,
        multiple_ok=True,
        helptext=helptext,
    )
    assert isinstance(option, list)
    return option


def _list_options(
    input_text: str,
    options: List[str],
    default_response: Optional[str],
    allow_custom_response: bool,
    multiple_ok: bool,
    pre_helptext: str,
    helptext: str,
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
        except Exception as _:  # TODO what is being caught here????
            if response is None and not multiple_ok:
                print(response, "received. Please input a response: ")
            if response == "" and default_response:
                response = default_response
                break
        if multiple_ok:
            try:
                response_nums = [int(x.strip()) for x in response.split(",")]
                response = [options[x - 1] for x in response_nums]
            except Exception as _:  # TODO what is being caught here????
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
