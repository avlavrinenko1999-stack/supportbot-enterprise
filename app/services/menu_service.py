from aiogram import Bot
from aiogram.types import BotCommand

from app.keyboards.admin import admin_main_menu
from app.keyboards.coordinator import coordinator_main_menu
from app.keyboards.operator import operator_main_menu
from app.keyboards.user_menu import user_main_menu
from app.models.account import Account
from app.models.enums import UserRole


class MenuService:
    @staticmethod
    async def setup_bot_commands(bot: Bot) -> None:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Открыть меню"),
                BotCommand(command="admin", description="Административное меню"),
            ]
        )

    @staticmethod
    def keyboard_for(account: Account):
        if account.role == UserRole.ADMIN:
            return admin_main_menu()

        if account.role == UserRole.COORDINATOR:
            return coordinator_main_menu()

        if account.role == UserRole.OPERATOR:
            return operator_main_menu()

        return user_main_menu()

    @staticmethod
    def title_for(account: Account) -> str:
        if account.role == UserRole.ADMIN:
            return "Административное меню."

        if account.role == UserRole.COORDINATOR:
            return "Меню координатора."

        if account.role == UserRole.OPERATOR:
            return "Меню оператора."

        return "Меню пользователя."
