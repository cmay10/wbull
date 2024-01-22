import uuid

class Account:
    def __init__(self,username,password):
        self.username = username
        self.password = password
        self.did = str(uuid.uuid4().hex)