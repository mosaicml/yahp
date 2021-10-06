from typing import List, Literal, Optional, Union, overload


class _InvalidResponseException(ValueError):
    pass


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
        print("Please respond with 'yes' or 'no' (or 'y' or 'n').")


def query_with_default(
    name: str,
    default_response: Optional[str] = None,
) -> str:
    default_response_pren = f" [{default_response}]" if default_response is not None else ""
    while True:
        try:
            response = input(f"{name}{default_response_pren}: ")
            if response.strip() == "":
                if default_response is None:
                    raise _InvalidResponseException("A response is required.")
                response = default_response
            return response
        except _InvalidResponseException as e:
            print(e.args[0])


def _parse_response(response: str, options: List[str]):
    option_lower_to_options = {x.lower(): x for x in options}
    try:
        response_num = int(response)
    except ValueError:
        response_val = response
    else:
        if response_num <= 0 or response_num > len(options):
            raise _InvalidResponseException(f"Value {response_num} is not a valid option")
        response_val = options[response_num - 1]
    if response_val.lower() in option_lower_to_options:
        return option_lower_to_options[response_val.lower()]
    raise _InvalidResponseException(f"Value {response_val} is not a valid option")


@overload
def query_with_options(name: str, options: List[str], default_response: Optional[str],
                       multiple_ok: Literal[False]) -> str:
    ...


@overload
def query_with_options(name: str, options: List[str], default_response: Optional[str],
                       multiple_ok: Literal[True]) -> List[str]:
    ...


def query_with_options(
    name: str,
    options: List[str],
    default_response: Optional[str],
    multiple_ok: bool,
) -> Union[str, List[str]]:
    default_response_pren = f" [{default_response}]" if default_response is not None else ""
    while True:
        try:
            print()
            print(name)
            print()
            for count, option in enumerate(options):
                print(f"{count + 1}): {option}")
            print()
            if multiple_ok:
                helptext = "Enter a number, value, or comma seperated numbers"
            else:
                helptext = "Enter a number or value"
            response = input(f"{helptext}{default_response_pren}: ").strip()
            if response == "":
                if default_response is None:
                    raise _InvalidResponseException("A response is required.")
                return [default_response] if multiple_ok else default_response
            if multiple_ok:
                responses = response.split(",")
                ans = []
                for x in responses:
                    ans.append(_parse_response(x, options))
                return ans
            else:
                return _parse_response(response, options)
        except _InvalidResponseException as e:
            print(e.args[0])
            # try again in the while loop
