import re
import os
import json
import streamlit as st
from pdfminer.high_level import extract_text


def extract_pdf_text(pdf_path):
    raw_text = extract_text(pdf_path)
    return clean_text(raw_text)  # Apply cleaning right after extraction


def split_questions(text):
    # Adjust pattern to match "Question #[number]"
    pattern = r'(Question #\d+)'
    parts = re.split(pattern, text)
    questions = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        content = parts[i + 1] if i + 1 < len(parts) else ''
        # Remove "Topic" information if present
        content = re.sub(r'Topic \d+', '', content).strip()
        questions.append({'heading': heading, 'content': content})
    return questions


def clean_text(text):
    # Remove 'Page N' or variations like "Page 2 of 5"
    text = re.sub(r'Page \d+( of \d+)?', '', text)
    # Remove excessive spaces and tabs
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove any blank lines
    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
    return text.strip()


def parse_question_content(question):
    content = clean_text(question['content'])
    # Find the position where answer choices start
    answer_start = re.search(r'\b[A-Z]\.\s', content)  # Match the first answer option
    if answer_start:
        question_body = content[:answer_start.start()].strip()
        answer_choices_text = content[answer_start.start():].strip()
    else:
        # If no answer choices found, treat the whole content as question body
        question_body = content
        answer_choices_text = ''

    # Process answer choices
    options = {}
    if answer_choices_text:
        # Dynamically match answer choices (e.g., 'A.', 'B.', ..., 'Z.')
        answer_choices = re.split(r'(?=[A-Z]\.\s)', answer_choices_text)
        for choice in answer_choices:
            choice = choice.strip()
            if not choice:
                continue
            # Match each option's letter and text
            option_match = re.match(r'^([A-Z])\.\s(.*)', choice, re.DOTALL)
            if option_match:
                option_letter = option_match.group(1)
                option_text = option_match.group(2).strip()
                options[option_letter] = option_text
    return question_body, options


def read_answer_key(answer_key_path):
    answer_key = {}
    try:
        with open(answer_key_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    # Adjust regex to match multiple letters (A-Z) separated by commas
                    match = re.match(r'^(\d+)\.\s*([A-Z](?:,\s*[A-Z])*)$', line)
                    if match:
                        question_number = int(match.group(1))
                        correct_answers = match.group(2)
                        # Split the correct answers into a list
                        correct_answers_list = [ans.strip() for ans in correct_answers.split(',')]
                        answer_key[question_number] = correct_answers_list
                    else:
                        print(f"Warning: Could not parse line in answer key: {line}")
    except FileNotFoundError:
        print(f"Answer key file not found: {answer_key_path}")
    return answer_key


def save_questions_to_json(questions_by_part, output_json_path):
    with open(output_json_path, 'w', encoding='utf-8') as json_file:
        json.dump(questions_by_part, json_file, indent=4, ensure_ascii=False)
    print(f"Questions saved to {output_json_path}")


def highlight_text(text, search_query):
    # Escape the search query for regex special characters
    escaped_query = re.escape(search_query)
    # Use regex to wrap the search query in a span with a subtle highlight style
    highlighted_text = re.sub(
        f"({escaped_query})",
        r"<span style='background-color: #f3f3f3; color: #333; padding: 2px; border-radius: 4px;'>\1</span>",
        text,
        flags=re.IGNORECASE  # Case-insensitive matching
    )
    return highlighted_text


def navigate_to_question(part_name, question_number):
    """Set query parameters to navigate to a specific question."""
    st.query_params = {'part': part_name, 'question': question_number}
    st.rerun()


def main():
    st.title("Practice Exam Simulator")

    # Handle query parameters using st.query_params
    query_params = st.query_params
    part_name = query_params.get("part", [None])[0]
    question_number = query_params.get("question", [None])[0]
    if question_number is not None:
        try:
            question_number = int(question_number)
        except ValueError:
            question_number = None

    # Load questions
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(current_dir, 'questions_by_part.json')

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            questions_by_part = json.load(f)
    except FileNotFoundError:
        st.error(f"File not found: {json_file}")
        return
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON from file: {json_file}")
        st.error(f"JSONDecodeError: {e}")
        return

    parts = list(questions_by_part.keys())

    if not parts:
        st.error("No parts found in the questions data.")
        return

    # Mode selection
    st.sidebar.header("Mode Selection")
    mode = st.sidebar.radio("Select Mode:", ("Exam Mode", "Practice Mode"))

    # Initialize session state for mode
    st.session_state["mode"] = mode

    # Initialize navigation if query parameters are present
    if part_name and question_number is not None:
        if part_name in questions_by_part:
            if part_name not in st.session_state:
                st.session_state[part_name] = {
                    'current_question': question_number - 1,
                    'answers': {},
                    'show_results': False,
                    'flagged': set()
                }
            else:
                st.session_state[part_name]['current_question'] = question_number - 1
                # Ensure 'flagged' key exists
                if 'flagged' not in st.session_state[part_name]:
                    st.session_state[part_name]['flagged'] = set()

    # Add Search Functionality
    st.sidebar.header("Search Questions")

    # Search input
    search_query = st.sidebar.text_input("Enter a keyword or phrase to search:")
    st.session_state["search_query"] = search_query

    # Add "Return to Exam" button in the sidebar
    if search_query:
        if st.sidebar.button("Return to Exam"):
            st.session_state["search_query"] = ""  # Clear the search query
            st.session_state.clear()  # Reset session state
            st.query_params = {}  # Clear query parameters
            st.rerun()

    search_results = []
    total_instances = 0

    if search_query:
        # Search across all parts
        for part_name_search, questions in questions_by_part.items():
            for question in questions:
                # Count occurrences in question text
                question_text_occurrences = len(re.findall(re.escape(search_query), question['question_text'], re.IGNORECASE))
                # Count occurrences in options
                option_occurrences = sum(
                    len(re.findall(re.escape(search_query), option_text, re.IGNORECASE))
                    for option_text in question['options'].values()
                )
                # Total occurrences in this question
                occurrences_in_question = question_text_occurrences + option_occurrences

                if occurrences_in_question > 0:
                    total_instances += occurrences_in_question

                    # Highlight the search query in the question text and options
                    highlighted_question_text = highlight_text(question['question_text'], search_query)
                    highlighted_options = {opt_key: highlight_text(opt_text, search_query) for opt_key, opt_text in question['options'].items()}

                    search_results.append({
                        'part_name': part_name_search,
                        'question_number': question['question_number'],
                        'question_text': highlighted_question_text,
                        'options': highlighted_options
                    })

        st.sidebar.write(f"Found {len(search_results)} questions relating to '{search_query}'")
        st.sidebar.write(f"There are {total_instances} instances of '{search_query}'")

    if search_results:
        st.subheader("Search Results")
        for result in search_results:
            # Display the part and question number
            st.markdown(f"**Part:** {result['part_name']}, **Question {result['question_number']}**")
            st.markdown(result['question_text'], unsafe_allow_html=True)

            # Display options
            for option, option_text in result['options'].items():
                st.markdown(f"- **{option}**: {option_text}", unsafe_allow_html=True)

            # Add "Go to Question" button
            if st.button(f"Go to Question {result['question_number']} in {result['part_name']}",
                         key=f"nav_{result['part_name']}_{result['question_number']}"):
                # Update session state to navigate to the specific question
                navigate_to_question(result['part_name'], result['question_number'])

            st.markdown("---")

    # Display flagged questions in the sidebar
    st.sidebar.header("Flagged Questions")
    any_flagged = False
    for part in parts:
        session_state_part = st.session_state.get(part, {})
        if 'flagged' not in session_state_part:
            session_state_part['flagged'] = set()
        flagged = session_state_part.get('flagged', set())
        if flagged:
            any_flagged = True
            st.sidebar.write(f"**{part}:**")
            for fq in sorted(flagged):
                if st.sidebar.button(f"Go to {part} Q{fq}", key=f"sidebar_flagged_{part}_{fq}"):
                    navigate_to_question(part, fq)
    if not any_flagged:
        st.sidebar.write("No flagged questions.")

    # Create tabs for each part
    tabs = st.tabs(parts)

    for idx, tab in enumerate(tabs):
        part_name_tab = parts[idx]
        with tab:
            st.header(part_name_tab)
            questions = questions_by_part[part_name_tab]
            total_questions = len(questions)

            # Initialize session state for this part
            if part_name_tab not in st.session_state:
                st.session_state[part_name_tab] = {
                    'current_question': 0,
                    'answers': {},
                    'show_results': False,
                    'flagged': set()
                }
            session_state = st.session_state[part_name_tab]

            # Ensure 'flagged' key exists
            if 'flagged' not in session_state:
                session_state['flagged'] = set()

            if not session_state['show_results']:
                question = questions[session_state['current_question']]
                question_number = question['question_number']
                is_flagged = question_number in session_state['flagged']
                flag_label = " ⚑" if is_flagged else ""
                st.subheader(f"Question {question_number} of {total_questions}{flag_label}")

                # Move Question Map to the top and make it collapsible
                # Question Map
                with st.expander("Question Map"):
                    cols = st.columns(10)
                    for i, q_num in enumerate(range(1, total_questions + 1)):
                        col = cols[i % 10]
                        label = f"{q_num}"
                        if q_num in session_state['flagged']:
                            label += " ⚑"
                        if col.button(label, key=f"qmap_{part_name_tab}_{q_num}"):
                            session_state['current_question'] = q_num - 1
                            st.rerun()

                # Display question text
                st.write("---")
                st.write(question['question_text'])

                options = question['options']
                option_keys = list(options.keys())

                # Determine if multiple answers are required
                correct_answer = question.get('correct_answer', [])
                num_correct = len(correct_answer)
                if num_correct > 1:
                    st.info(f"This question requires selecting {num_correct} answers.")
                    # Use checkboxes for multiple selection
                    selected_options = []
                    for key in option_keys:
                        checkbox_id = f"{part_name_tab}_{session_state['current_question']}_{key}"
                        checked = key in session_state['answers'].get(question_number, [])
                        if st.checkbox(f"{key}. {options[key]}", key=checkbox_id, value=checked):
                            selected_options.append(key)
                        else:
                            # Ensure options are removed if unchecked
                            if key in selected_options:
                                selected_options.remove(key)
                    # Save the selected options
                    session_state['answers'][question_number] = selected_options
                else:
                    st.info("This question requires selecting 1 answer.")
                    # Use radio buttons for single selection
                    radio_id = f"{part_name_tab}_{session_state['current_question']}"
                    previous_selection = session_state['answers'].get(question_number, [])
                    if previous_selection and previous_selection[0] in option_keys:
                        index = option_keys.index(previous_selection[0])
                    else:
                        index = 0
                    selected_option = st.radio(
                        "Select your answer:",
                        [f"{key}. {options[key]}" for key in option_keys],
                        index=index,
                        key=radio_id
                    )
                    selected_letter = selected_option.split('.')[0]
                    # Save the selected option
                    session_state['answers'][question_number] = [selected_letter]

                # Flagging option
                is_flagged = question_number in session_state['flagged']
                if st.checkbox("Flag this question", value=is_flagged, key=f"flag_{part_name_tab}_{question_number}"):
                    # Add question to flagged set
                    session_state['flagged'].add(question_number)
                else:
                    # Remove question from flagged set if it was flagged
                    session_state['flagged'].discard(question_number)

                # Navigation controls
                st.write("---")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Previous", key=f"prev_{part_name_tab}_{session_state['current_question']}"):
                        if session_state['current_question'] > 0:
                            session_state['current_question'] -= 1
                            st.rerun()
                with col2:
                    if st.button("Next", key=f"next_{part_name_tab}_{session_state['current_question']}"):
                        if session_state['current_question'] < total_questions - 1:
                            session_state['current_question'] += 1
                            st.rerun()
                with col3:
                    if st.button("Submit Exam", key=f"submit_{part_name_tab}"):
                        session_state['show_results'] = True
                        st.rerun()

                # Behavior based on mode
                if st.session_state["mode"] == "Practice Mode":
                    # "Check Answer" button
                    if st.button("Check Answer", key=f"check_{part_name_tab}_{session_state['current_question']}"):
                        selected_options = session_state['answers'][question_number]
                        if len(selected_options) != num_correct:
                            st.warning(f"Please select exactly {num_correct} answer(s) before checking.")
                        else:
                            # Check if the selected options match the correct answers
                            if set(selected_options) == set(correct_answer):
                                st.success("Correct!")
                            else:
                                st.error("Incorrect.")
                                st.markdown("**Correct answer(s):**")
                                for opt in correct_answer:
                                    st.markdown(f"- **{opt}. {options.get(opt, 'Option not found')}**")
                else:
                    # Exam Mode: Do not show immediate feedback
                    pass  # No immediate feedback in Exam Mode

            else:
                st.header("Exam Results")

                correct_answers_count = 0
                for idx_q, question in enumerate(questions):
                    question_number = question['question_number']
                    st.subheader(f"Question {question_number}")
                    st.write(question['question_text'])

                    options = question['options']
                    selected_options = session_state['answers'].get(question_number, [])
                    correct_options = question.get('correct_answer', [])
                    is_correct = set(selected_options) == set(correct_options)

                    # Display user's answer
                    if selected_options:
                        selected_display = ', '.join([f"{opt}. {options.get(opt, '')}" for opt in selected_options])
                        if is_correct:
                            st.success(f"Your answer: {selected_display}")
                        else:
                            st.error(f"Your answer: {selected_display}")
                            st.markdown("**Correct answer(s):**")
                            for opt in correct_options:
                                st.markdown(f"- **{opt}. {options.get(opt, 'Option not found')}**")
                    else:
                        st.warning("Your answer: No answer selected")
                        if correct_options:
                            st.markdown("**Correct answer(s):**")
                            for opt in correct_options:
                                st.markdown(f"- **{opt}. {options.get(opt, 'Option not found')}**")

                    if is_correct:
                        correct_answers_count += 1

                # Display total score
                percentage_score = (correct_answers_count / total_questions) * 100
                st.write(f"Your total score: {correct_answers_count} out of {total_questions} ({percentage_score:.2f}%)")

                if st.button("Retake Exam", key=f"retake_{part_name_tab}"):
                    session_state['current_question'] = 0
                    session_state['answers'] = {}
                    session_state['show_results'] = False
                    session_state['flagged'] = set()
                    st.rerun()

    st.write(st.__version__)
if __name__ == "__main__":
    main()
