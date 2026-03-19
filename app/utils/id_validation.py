# utils/id_validation.py 
def validate_israeli_id_checksum(id_number: str) -> bool:
    if len(id_number) != 9 or not id_number.isdigit():
        return False
    total = 0
    for i, digit in enumerate(id_number):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0