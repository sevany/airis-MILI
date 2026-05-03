from elevenlabs import generate, set_api_key

# Use your new key
set_api_key("sk_556dbcb6eada34ff0776c4bb56409da3f5b376285b909d5e")

# Test
audio = generate(
    text="Test, why this shit isnt working, imt rying so hard right now",
    voice="6u6JbqKdaQy89ENzLSju",
    model="eleven_multilingual_v2"
)

print("Success!" if audio else "Failed!")