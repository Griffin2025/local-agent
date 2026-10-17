def calculate_total(price, tax):
  discount = 0
  total = (price + tax) - discount
  return total

print(calculate_total(100, 5))