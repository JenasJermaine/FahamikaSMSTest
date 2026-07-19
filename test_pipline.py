from pipeline import process_message

# Test with a known keyword
reply = process_message("Tell me about disability rights")
print("=" * 40)
print("REPLY:")
print(reply)