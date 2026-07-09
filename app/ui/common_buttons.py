from enum import StrEnum

from app.i18n import tr


class CommonButton(StrEnum):
    BACK = "back"
    CANCEL = "cancel"
    SAVE = "save"
    DELETE = "delete"
    EDIT = "edit"
    CREATE = "create"
    SEARCH = "search"
    YES = "yes"
    NO = "no"
    NEXT = "next"
    PREV = "prev"
    ADMIN_MENU = "admin_menu"


COMMON_BUTTON_TEXT_KEYS = {
    CommonButton.BACK: "button.back",
    CommonButton.CANCEL: "button.cancel",
    CommonButton.SAVE: "button.save",
    CommonButton.DELETE: "button.delete",
    CommonButton.EDIT: "button.edit",
    CommonButton.CREATE: "button.create",
    CommonButton.SEARCH: "button.search",
    CommonButton.YES: "button.yes",
    CommonButton.NO: "button.no",
    CommonButton.NEXT: "button.next",
    CommonButton.PREV: "button.prev",
    CommonButton.ADMIN_MENU: "button.admin_menu",
}


def common_button(language: str, button: CommonButton) -> str:
    return tr(language, COMMON_BUTTON_TEXT_KEYS[button])
