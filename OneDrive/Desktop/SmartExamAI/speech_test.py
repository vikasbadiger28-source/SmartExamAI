import speech_recognition as sr

recognizer = sr.Recognizer()

with sr.Microphone() as source:
    print("🎤 Speak now...")
    recognizer.adjust_for_ambient_noise(source)
    audio = recognizer.listen(source)

try:
    print("🔎 Converting speech to text...")
    text = recognizer.recognize_google(audio)
    print("📝 You said:")
    print(text)

except sr.UnknownValueError:
    print("Sorry, could not understand audio")

except sr.RequestError:
    print("Could not request results. Check internet connection.")