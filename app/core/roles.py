from rolepermissions.roles import AbstractUserRole


class ReadOnly(AbstractUserRole):
    available_permissions = {
        'read_data': True
    }


class WriteOnly(AbstractUserRole):
    available_permissions = {
        'write_data': True
    }


class SystemAdmin(AbstractUserRole):
    available_permissions = {
        'admin': True
    }


class Data(AbstractUserRole):
    available_permissions = {
        'data': True
    }
