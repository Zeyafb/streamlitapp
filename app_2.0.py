import re
import os
import json
import random
import streamlit as st

# Set default layout to wide mode
st.set_page_config(layout="wide")

def highlight_text(text, phrases):
    """Highlights a list of phrases within the given text."""
    if not phrases:
        return text
    # Escape and join phrases into a single regex pattern
    escaped_phrases = [re.escape(phrase) for phrase in phrases]
    pattern = '|'.join(escaped_phrases)
    highlighted_text = re.sub(
        f"({pattern})",
        r"<mark>\1</mark>",
        text,
        flags=re.IGNORECASE
    )
    return highlighted_text

def navigate_to_question(exam_session, question_number):
    """Navigates to a specific question in the exam."""
    if exam_session:
        exam_session['current_question'] = question_number - 1
        st.rerun()
    else:
        st.error("No exam is currently active.")

def display_question(question, selected_options):
    """Displays the question and options, and returns updated selected options."""
    st.write("---")
    
    # Display the question text
    question_text = question['question_text']
    st.write(question_text)
    
    # Display the options
    options = question['options']
    option_keys = list(options.keys())
    correct_answer = question.get('correct_answer', [])
    num_correct = len(correct_answer)
    
    if num_correct > 1:
        st.info(f"This question requires selecting {num_correct} answers.")
        new_selected_options = []
        for key in option_keys:
            checkbox_id = f"{question['question_number']}_{key}"
            checked = key in selected_options
            option_text = f"{key}. {options[key]}"
            if st.checkbox(option_text, key=checkbox_id, value=checked):
                new_selected_options.append(key)
        return new_selected_options
    else:
        st.info("This question requires selecting 1 answer.")
        radio_id = f"{question['question_number']}"
        options_list = [f"{key}. {options[key]}" for key in option_keys]
        if selected_options and selected_options[0] in option_keys:
            index = option_keys.index(selected_options[0])
        else:
            index = None  # No option selected
        selected_option = st.radio(
            "Select your answer:",
            options_list,
            index=index,
            key=radio_id
        )
        if selected_option:
            selected_letter = selected_option.split('.')[0]
            return [selected_letter]
        else:
            return []

def display_navigation_controls(session_state, total_questions):
    """Displays navigation controls for the exam."""
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous", key=f"prev_{session_state['current_question']}"):
            if session_state['current_question'] > 0:
                session_state['current_question'] -= 1
                st.rerun()
    with col2:
        if st.button("Next", key=f"next_{session_state['current_question']}"):
            if session_state['current_question'] < total_questions - 1:
                session_state['current_question'] += 1
                st.rerun()

def display_question_map(session_state, total_questions):
    """Displays a collapsible question map."""
    with st.expander("Question Map"):
        cols = st.columns(10)
        for i, q_num in enumerate(range(1, total_questions + 1)):
            col = cols[i % 10]
            label = f"{q_num}"
            if col.button(label, key=f"qmap_{q_num}"):
                session_state['current_question'] = q_num - 1
                st.rerun()

def save_exam_history(exam_history):
    """Saves the exam history to a JSON file."""
    try:
        with open('exam_history.json', 'w', encoding='utf-8') as f:
            json.dump(exam_history, f)
    except Exception as e:
        st.error(f"Error saving exam history: {e}")

def load_exam_history():
    """Loads the exam history from a JSON file."""
    if os.path.exists('exam_history.json'):
        try:
            with open('exam_history.json', 'r', encoding='utf-8') as f:
                exam_history = json.load(f)
            # Convert keys back to integers if necessary
            return exam_history
        except Exception as e:
            st.error(f"Error loading exam history: {e}")
            return {}
    else:
        return {}

def main():
    st.title("Practice Exam Simulator")

    # Load exam history from file
    if 'exam_history' not in st.session_state:
        st.session_state['exam_history'] = load_exam_history()

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

    # Combine all questions from all parts
    all_questions = []
    for questions in questions_by_part.values():
        all_questions.extend(questions)
    if len(all_questions) < 65:
        st.error("Not enough questions available to generate a 65-question exam.")
        return

    # Sidebar - Start New Exam
    st.sidebar.header("Start a New Practice Test")
    start_exam = st.sidebar.button("Start New Practice Test", key='start_exam')

    # Sidebar - Exam History with Keyword Search
    st.sidebar.header("Exam History")

    # Search box
    exam_search_query = st.sidebar.text_input("Search Exams", key='search_exams')

    # Filter exams based on search query in exam content
    filtered_exams = {}
    for eid, ex in st.session_state['exam_history'].items():
        exam_matches = False
        # Check if search_query matches exam ID
        if exam_search_query.lower() in eid.lower():
            exam_matches = True
        else:
            # Search within questions and answers
            for q in ex['questions']:
                if exam_search_query.lower() in q['question_text'].lower():
                    exam_matches = True
                    break
                for opt_key, opt_text in q['options'].items():
                    if exam_search_query.lower() in opt_text.lower():
                        exam_matches = True
                        break
                if exam_matches:
                    break
        if exam_matches:
            filtered_exams[eid] = ex

    # Display filtered exams
    if filtered_exams:
        for eid, ex in filtered_exams.items():
            status = 'Completed' if ex['completed'] else 'In Progress'
            if st.sidebar.button(f"{eid} ({status})", key=f"history_{eid}"):
                st.session_state['current_exam'] = eid
                st.rerun()
    else:
        st.sidebar.write("No exams found.")

    # Search functionality for all questions
    st.sidebar.header("Search Questions")
    search_query = st.sidebar.text_input("Enter a keyword or phrase to search:", key='question_search_query')

    search_results = []
    total_instances = 0

    if search_query:
        for part_name_search, questions in questions_by_part.items():
            for question in questions:
                question_text_occurrences = len(re.findall(re.escape(search_query), question['question_text'], re.IGNORECASE))
                option_occurrences = sum(
                    len(re.findall(re.escape(search_query), option_text, re.IGNORECASE))
                    for option_text in question['options'].values()
                )
                occurrences_in_question = question_text_occurrences + option_occurrences

                if occurrences_in_question > 0:
                    total_instances += occurrences_in_question
                    highlighted_question_text = highlight_text(question['question_text'], [search_query])
                    highlighted_options = {opt_key: highlight_text(opt_text, [search_query]) for opt_key, opt_text in question['options'].items()}

                    search_results.append({
                        'part_name': part_name_search,
                        'question_number': question['question_number'],
                        'question_text': highlighted_question_text,
                        'options': highlighted_options,
                        'question_data': question  # Include full question data for navigation
                    })

        st.sidebar.write(f"Found {len(search_results)} questions relating to '{search_query}'")
        st.sidebar.write(f"There are {total_instances} instances of '{search_query}'")

    if search_results:
        st.subheader("Search Results")
        for result in search_results:
            st.markdown(f"**Part:** {result['part_name']}, **Question {result['question_number']}**", unsafe_allow_html=True)
            st.markdown(result['question_text'], unsafe_allow_html=True)

            for option, option_text in result['options'].items():
                st.markdown(f"- **{option}**: {option_text}", unsafe_allow_html=True)

            if st.button(f"Go to Question {result['question_number']} in Current Exam", key=f"nav_{result['question_number']}"):
                if 'current_exam' in st.session_state:
                    exam_session = st.session_state['exam_history'][st.session_state['current_exam']]
                    # Find the question in the current exam
                    for idx, q in enumerate(exam_session['questions']):
                        if q['question_text'] == result['question_data']['question_text']:
                            navigate_to_question(exam_session, idx + 1)
                            break
                    else:
                        st.error("Question not found in current exam.")
                else:
                    st.error("No exam is currently active. Please start a new exam first.")

            st.markdown("---")

    # Handle starting a new exam
    if start_exam:
        # Generate a new random exam
        random_questions = random.sample(all_questions, 65)
        # Assign sequential question numbers
        for idx, question in enumerate(random_questions):
            question['question_number'] = idx + 1
        exam_id = f"Exam_{len(st.session_state['exam_history']) + 1}"
        exam_session = {
            'exam_id': exam_id,
            'questions': random_questions,
            'current_question': 0,
            'answers': {},
            'completed': False,
            'score': None,
        }
        # Save the exam to history
        st.session_state['exam_history'][exam_id] = exam_session
        st.session_state['current_exam'] = exam_id
        save_exam_history(st.session_state['exam_history'])  # Save to file
        st.rerun()

    # Display the current exam if one is active and not searching
    if 'current_exam' in st.session_state and not search_query:
        exam_session = st.session_state['exam_history'][st.session_state['current_exam']]
        display_exam_interface(exam_session)
    elif not search_query:
        st.write("Click 'Start New Practice Test' in the sidebar to begin.")

def display_exam_interface(exam_session):
    """Displays the interface for the exam."""
    exam = exam_session
    questions = exam['questions']
    total_questions = len(questions)
    current_question_index = exam['current_question']
    question = questions[current_question_index]
    question_number = current_question_index + 1  # Adjusted to reflect position in the exam
    st.subheader(f"Question {question_number} of {total_questions}")

    # Display question map
    display_question_map(exam, total_questions)

    # Display question and get updated selected options
    selected_options = exam['answers'].get(question_number, [])
    new_selected_options = display_question(question, selected_options)
    exam['answers'][question_number] = new_selected_options

    # Navigation controls
    display_navigation_controls(exam, total_questions)

    # Submit Exam functionality
    if not exam['completed'] and st.button("Submit Exam"):
        # Grade the exam
        correct_count = 0
        for idx, q in enumerate(questions):
            q_num = idx + 1
            selected_options = exam['answers'].get(q_num, [])
            correct_answer = q.get('correct_answer', [])
            if set(selected_options) == set(correct_answer):
                correct_count += 1
        score = correct_count / total_questions * 100
        exam['score'] = score
        exam['completed'] = True
        st.success(f"You scored {correct_count} out of {total_questions} ({score:.2f}%)")
        st.session_state['exam_history'][exam['exam_id']] = exam
        save_exam_history(st.session_state['exam_history'])  # Save to file

    if exam['completed']:
        st.success(f"Exam completed. Your score: {exam['score']:.2f}%")
        if st.button("Review Exam"):
            for idx, q in enumerate(questions):
                q_num = idx + 1
                st.write("---")
                st.write(f"**Question {q_num}:**")
                st.write(q['question_text'])
                options = q['options']
                selected_options = exam['answers'].get(q_num, [])
                correct_answer = q.get('correct_answer', [])
                for opt_key, opt_text in options.items():
                    opt_label = f"{opt_key}. {opt_text}"
                    if opt_key in correct_answer and opt_key in selected_options:
                        st.write(f"- ✅ **{opt_label}**")
                    elif opt_key in correct_answer:
                        st.write(f"- 🟩 **{opt_label} (Correct Answer)**")
                    elif opt_key in selected_options:
                        st.write(f"- ❌ {opt_label}")
                    else:
                        st.write(f"- {opt_label}")

    # Option to go back to exam list
    if st.button("Back to Exam List"):
        del st.session_state['current_exam']
        st.rerun()

if __name__ == "__main__":
    main()
