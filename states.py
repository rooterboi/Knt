from aiogram.fsm.state import State, StatesGroup


class PromoStates(StatesGroup):
    waiting_code = State()


class AddAdminStates(StatesGroup):
    waiting_id = State()


class RemoveAdminStates(StatesGroup):
    waiting_id = State()


class AddMovieStates(StatesGroup):
    waiting_file = State()
    waiting_poster = State()
    waiting_title = State()
    waiting_code = State()
    waiting_description = State()
    waiting_access = State()


class AddEpisodeStates(StatesGroup):
    waiting_code = State()
    waiting_title = State()
    waiting_season = State()
    waiting_episode = State()
    waiting_file = State()
    waiting_access = State()


class PromoCreateStates(StatesGroup):
    waiting_code = State()
    waiting_amount = State()
    waiting_limit = State()


class UserManageStates(StatesGroup):
    waiting_id_for_premium = State()
    waiting_id_for_balance = State()
    waiting_balance_amount = State()


class BroadcastStates(StatesGroup):
    waiting_message = State()


class ChannelStates(StatesGroup):
    waiting_add = State()
    waiting_remove = State()


class PostChannelStates(StatesGroup):
    waiting_channel = State()


class SettingsStates(StatesGroup):
    waiting_referral_bonus = State()
    waiting_price_1m = State()
    waiting_price_3m = State()
    waiting_price_lifetime = State()


class SearchStates(StatesGroup):
    waiting_code = State()


class DeleteMovieStates(StatesGroup):
    waiting_code = State()
