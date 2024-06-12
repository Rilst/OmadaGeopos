from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class SizesCallbackFactory(CallbackData, prefix="sizesfub"):
    article: str
    size: str

async def GenerateKeybordSizes(card):
    builder = InlineKeyboardBuilder()
    for size in card['sizes']:
        builder.button(text = size, callback_data=SizesCallbackFactory(
            size=size, article=card['article']
            ))
    builder.adjust(3)
    return builder.as_markup()
