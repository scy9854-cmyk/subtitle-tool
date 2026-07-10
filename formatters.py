def format_bible(data: dict) -> str:
    ref = f"{data['book']} {data['chapter']}:{data['start']}"
    if data["end"] != data["start"]:
        ref += f"-{data['end']}"

    blocks = [f"{ref}\n{num}. {text}" for num, text in data["verses"]]
    return "\n\n".join(blocks)
