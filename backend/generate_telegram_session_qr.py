import asyncio

import qrcode
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 38777418
API_HASH = "51c587bfe043c480e7456eb661945034"


async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        qr_login = await client.qr_login()
        print("Scan this QR in Telegram: Settings -> Devices -> Link Desktop Device")
        qr = qrcode.QRCode(border=1)
        qr.add_data(qr_login.url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
        await qr_login.wait()

        if not await client.is_user_authorized():
            print("Authorization did not complete.")
            return

        me = await client.get_me()
        print(f"Authorized as: {getattr(me, 'first_name', '')} {getattr(me, 'last_name', '')}".strip())
        print("\nSESSION_STRING:\n")
        print(client.session.save())
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
