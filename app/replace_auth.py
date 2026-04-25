# Script to replace get_current_user with a mock user

def replace_get_current_user(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Find the start and end of the get_current_user function
    start_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('def get_current_user'):
            start_idx = i
            break

    if start_idx == -1:
        print('ERROR: Could not find get_current_user function')
        return False

    # Find the end of the function: look for the next line that starts with 'def ' (after start_idx) or end of file.
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip().startswith('def '):
            end_idx = i
            break

    # Build the new function lines
    new_function_lines = [
        'def get_current_user(authorization: str | None = Header(default=None)) -> dict:\n',
        '    return {\n',
        '        \"id\": 1,\n',
        '        \"email\": \"demo@example.com\",\n',
        '        \"is_admin\": True,\n',
        '        \"is_active\": True,\n',
        '        \"name\": \"Demo User\",\n',
        '        \"avatar_url\": None,\n',
        '        \"custom_avatar_url\": None,\n',
        '        \"social_avatar_url\": None,\n',
        '        \"blog\": \"\",\n',
        '        \"location\": \"\",\n',
        '        \"email_verified\": True,\n',
        '    }\n'
    ]

    # Replace
    lines[start_idx:end_idx] = new_function_lines

    with open(file_path, 'w') as f:
        f.writelines(lines)

    print('Successfully replaced get_current_user with mock user from line {} to line {}.'.format(start_idx+1, end_idx))
    return True

if __name__ == '__main__':
    replace_get_current_user('main.py')