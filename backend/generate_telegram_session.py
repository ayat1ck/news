import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    ApiIdInvalidError,
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    PhoneNumberFloodError,
    RpcCallFailError,
    SessionPasswordNeededError,
)

API_ID = 38777418
API_HASH = "51c587bfe043c480e7456eb661945034"


def describe_sent_code(sent) -> None:
    sent_type = getattr(sent, "type", None)
    next_type = getattr(sent, "next_type", None)
    timeout = getattr(sent, "timeout", None)

    print("Code request diagnostics:")
    print(f"  phone_code_hash: {getattr(sent, 'phone_code_hash', None)}")
    print(f"  type: {sent_type!r}")
    print(f"  next_type: {next_type!r}")
    print(f"  timeout: {timeout!r}")


async def main():
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        phone = input("Phone (+7...): ").strip()
        sent = await client.send_code_request(phone)
        print("Code request sent.")
        describe_sent_code(sent)
        print("Check Telegram app/Desktop for a fresh login code, not my.telegram.org.")

        code = input("Code from Telegram: ").strip()

        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
        except SessionPasswordNeededError:
            password = input("2FA password: ").strip()
            await client.sign_in(password=password)
        except PhoneCodeInvalidError:
            print("Invalid code. Request a new one and try again.")
            return
        except PhoneCodeExpiredError:
            print("Code expired. Request a new one and try again.")
            return
        except PhoneNumberInvalidError:
            print("Phone number is invalid. Use international format like +7706...")
            return
        except PhoneNumberFloodError:
            print("Too many attempts for this phone number. Wait and try again later.")
            return
        except FloodWaitError as exc:
            print(f"Telegram asked to wait {exc.seconds} seconds before trying again.")
            return
        except PasswordHashInvalidError:
            print("Invalid 2FA password.")
            return
        except ApiIdInvalidError:
            print("API_ID or API_HASH is invalid.")
            return
        except RpcCallFailError as exc:
            print(f"Telegram RPC call failed: {exc}")
            return

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
