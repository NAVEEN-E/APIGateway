from uuid import UUID


def is_valid_uuid(uuid_string):
    try:
        valid = UUID(uuid_string, version=4)
    except ValueError:
        return False

    return True
