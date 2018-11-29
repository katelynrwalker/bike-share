'''
In mid November, JUMP added a field to their API. 
This will wreak havoc on a csv file that spans this period! 
Particularly when you try to read it into pandas.
Here is a quick script to remove that extra field.
'''

def cleaner(input_path, output_path):
    with open(input_path, 'r') as csvfile:
        output = open(output_path, 'w')
        for row in csvfile:
            cleaned = row.replace('bike,', '')
            output.write(cleaned)
        output.close()