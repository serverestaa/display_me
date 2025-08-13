import google.generativeai as genai, os
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")

async def write_cover_letter(description: str) -> str:
    prompt = f"""Write 2 sentences introducing me, highlight relevant skills 
                 and enthusiasm for the role below: ――
                 {description[:1500]}"""
    resp = model.generate_content(prompt, safety_settings={"category":"cover_letter"})
    return resp.text.strip()
