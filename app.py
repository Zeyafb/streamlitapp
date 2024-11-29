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

def initialize_part_session_state(part_name):
    """Initializes the session state for a given part."""
    if part_name not in st.session_state:
        st.session_state[part_name] = {
            'current_question': 0,
            'answers': {},
        }

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

def display_navigation_controls(session_state, total_questions, exam_id):
    """Displays navigation controls for the exam."""
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous", key=f"prev_{exam_id}_{session_state['current_question']}"):
            if session_state['current_question'] > 0:
                session_state['current_question'] -= 1
                st.rerun()
    with col2:
        if st.button("Next", key=f"next_{exam_id}_{session_state['current_question']}"):
            if session_state['current_question'] < total_questions - 1:
                session_state['current_question'] += 1
                st.rerun()

def display_question_map(session_state, total_questions, exam_id):
    """Displays a collapsible question map."""
    with st.expander("Question Map"):
        cols = st.columns(10)
        for i, q_num in enumerate(range(1, total_questions + 1)):
            col = cols[i % 10]
            label = f"{q_num}"
            if col.button(label, key=f"qmap_{exam_id}_{q_num}"):
                session_state['current_question'] = q_num - 1
                st.rerun()

def main():
    st.title("Practice Exam Simulator")

    # Initialize exam history
    if 'exam_history' not in st.session_state:
        st.session_state['exam_history'] = {}

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

    # Part selection
    st.sidebar.header("Select Part")
    parts = list(questions_by_part.keys())
    if 'selected_part' not in st.session_state:
        st.session_state['selected_part'] = parts[0]
    parts.append('Random Exam')
    selected_part = st.sidebar.selectbox("Choose a part or take a random exam:", parts, index=parts.index(st.session_state['selected_part']))
    st.session_state['selected_part'] = selected_part
    part_name = selected_part

    # Check if 'Random Exam' is selected
    if part_name == 'Random Exam':
        # Show a button to start a new random exam
        if st.sidebar.button("Start New Random Exam"):
            # Generate a new random exam
            all_questions = []
            for questions in questions_by_part.values():
                all_questions.extend(questions)
            if len(all_questions) < 65:
                st.error("Not enough questions available to generate a 65-question exam.")
                return
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
            # Set the current exam
            st.session_state['current_exam'] = exam_id
            st.session_state['random_exam'] = exam_session
            st.experimental_rerun()
        else:
            # Check if there is an ongoing or selected exam
            if 'current_exam' in st.session_state:
                exam_id = st.session_state['current_exam']
                exam_session = st.session_state['exam_history'][exam_id]
                # Display the exam interface
                exam = exam_session
                questions = exam['questions']
                total_questions = len(questions)
                current_question_index = exam['current_question']
                question = questions[current_question_index]
                question_number = question['question_number']
                st.subheader(f"Question {question_number} of {total_questions}")

                # Display question map
                display_question_map(exam, total_questions, exam_id)

                # Display question and get updated selected options
                selected_options = exam['answers'].get(question_number, [])
                new_selected_options = display_question(question, selected_options)
                exam['answers'][question_number] = new_selected_options

                # Navigation controls
                display_navigation_controls(exam, total_questions, exam_id)

                # Check Answer functionality
                if st.button("Check Answer", key=f"check_random_exam_{current_question_index}"):
                    selected_options = exam['answers'][question_number]
                    correct_answer = question.get('correct_answer', [])
                    num_correct = len(correct_answer)
                    if len(selected_options) != num_correct:
                        st.warning(f"Please select exactly {num_correct} answer(s) before checking.")
                    else:
                        if set(selected_options) == set(correct_answer):
                            st.success("Correct!")
                        else:
                            st.error("Incorrect.")
                            st.markdown("**Correct answer(s):**")
                            for opt in correct_answer:
                                st.markdown(f"- **{opt}. {question['options'].get(opt, 'Option not found')}**")

                # Submit Exam functionality
                if not exam['completed'] and st.button("Submit Exam"):
                    # Grade the exam
                    correct_count = 0
                    total_questions = len(questions)
                    for q in questions:
                        q_num = q['question_number']
                        selected_options = exam['answers'].get(q_num, [])
                        correct_answer = q.get('correct_answer', [])
                        if set(selected_options) == set(correct_answer):
                            correct_count += 1
                    score = correct_count / total_questions * 100
                    exam['score'] = score
                    exam['completed'] = True
                    st.success(f"You scored {correct_count} out of {total_questions} ({score:.2f}%)")
                    # Save the exam to history
                    exam_id = exam['exam_id']
                    st.session_state['exam_history'][exam_id] = exam

                if exam['completed']:
                    st.success(f"Exam completed. Your score: {exam['score']:.2f}%")
                    # Optionally, provide a 'Review Exam' button
                    if st.button("Review Exam"):
                        # Allow user to review their answers
                        for q in questions:
                            q_num = q['question_number']
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
                    # Provide option to start a new exam
                    if st.button("Start a New Random Exam"):
                        del st.session_state['current_exam']
                        st.experimental_rerun()
            else:
                st.write("Click the 'Start New Random Exam' button in the sidebar to begin.")

        # Show the exam history
        st.sidebar.header("Exam History")
        for eid, ex in st.session_state['exam_history'].items():
            status = 'Completed' if ex['completed'] else 'In Progress'
            if st.sidebar.button(f"{eid} ({status})", key=f"history_{eid}"):
                st.session_state['current_exam'] = eid
                st.experimental_rerun()
    else:
        # Regular part selected
        # Initialize session state for navigation
        initialize_part_session_state(part_name)

        session_state = st.session_state[part_name]

        st.header(part_name)
        questions = questions_by_part[part_name]
        total_questions = len(questions)

        question = questions[session_state['current_question']]
        question_number = question['question_number']
        st.subheader(f"Question {question_number} of {total_questions}")

        # Display question map
        display_question_map(session_state, total_questions, part_name)

        # Display question and get updated selected options
        selected_options = session_state['answers'].get(question_number, [])
        new_selected_options = display_question(question, selected_options)
        session_state['answers'][question_number] = new_selected_options

        # Navigation controls
        display_navigation_controls(session_state, total_questions, part_name)

        # Check Answer functionality
        if st.button("Check Answer", key=f"check_{part_name}_{session_state['current_question']}"):
            selected_options = session_state['answers'][question_number]
            correct_answer = question.get('correct_answer', [])
            num_correct = len(correct_answer)
            if len(selected_options) != num_correct:
                st.warning(f"Please select exactly {num_correct} answer(s) before checking.")
            else:
                if set(selected_options) == set(correct_answer):
                    st.success("Correct!")
                else:
                    st.error("Incorrect.")
                    st.markdown("**Correct answer(s):**")
                    for opt in correct_answer:
                        st.markdown(f"- **{opt}. {question['options'].get(opt, 'Option not found')}**")

if __name__ == "__main__":
    main()
