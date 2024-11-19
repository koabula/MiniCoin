import hashlib

data = "hello blockchain"

data_digest = hashlib.sha256()
data_digest.update(data.encode())

print(data_digest.hexdigest())