from deep_translator import MyMemoryTranslator, GoogleTranslator

try:
    print("Testing MyMemory...")
    res1 = MyMemoryTranslator(source="en-US", target="es-ES").translate("Hello, welcome to this video!")
    print("MyMemory result:", repr(res1))
except Exception as e:
    print("MyMemory error:", e)

try:
    print("Testing Google batch or text...")
    res2 = GoogleTranslator(source="auto", target="es").translate("Hello, welcome to this video!")
    print("Google result:", repr(res2))
except Exception as e:
    print("Google error:", e)
