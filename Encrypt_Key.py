from cryptography.fernet import Fernet

# Your Fernet key from Step 2
fernet_key = b'yyHnmjkbF472mjnqjqbQjbzwW-q2MVhcsKMJWugrY_I='  # Replace with the key from Step 2
fernet = Fernet(fernet_key)

# Your Deepseek API key
api_key = "sk-5ca2f4bbc391429cb52ce4e2e7825094"  # Replace with your real key

# Encrypt it
encrypted_key = fernet.encrypt(api_key.encode())
print("Encrypted API key:", encrypted_key.decode())