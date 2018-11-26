def cleaner(input_path, output_path):
    with open(input_path, 'r') as csvfile:
        output = open(output_path, 'w')
        for row in csvfile:
            cleaned = row.replace('bike,', '')
            output.write(cleaned)
        output.close()