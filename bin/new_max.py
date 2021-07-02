from firebase_admin.messaging import MulticastMessage

from fcm_django.models import MAX_MESSAGES_PER_BATCH


def run():
    # Run until we can get a verifiable output
    for x in range(1000000, 0, -100):
        try:
            MulticastMessage([""] * x)
        except ValueError:
            continue
        if x != MAX_MESSAGES_PER_BATCH:
            print(f"New number: {x}")
        else:
            print("Nothing new")
        break


if __name__ == "__main__":
    run()
