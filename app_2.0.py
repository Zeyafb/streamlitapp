import re
import os
import json
import random
import streamlit as st

# Set default layout to wide mode
st.set_page_config(layout="wide")

def highlight_text(text, color):
    """Wraps the text in HTML to highlight it with the given color."""
    return f"<div style='background-color: {color}; padding: 5px'>{text}</div>"

def navigate_to_question(exam_session, question_number):
    """Navigates to a specific question in the exam."""
    if exam_session:
        exam_session['current_question'] = question_number - 1
        st.rerun()
    else:
        st.error("No exam is currently active.")

def display_question(exam_session, question, selected_options):
    """Displays the question and options, and handles user interactions."""
    st.write("---")

    # Display the question text
    question_text = question['question_text']
    st.write(question_text)
    # Display the origin of the question
    question_origin_html = f"""
    <div class='question-origin'>Source: {question['origin']}</div>
    """
    st.markdown(question_origin_html, unsafe_allow_html=True)
    # Display the options
    options = question['options']
    option_keys = list(options.keys())
    correct_answer = question.get('correct_answer', [])
    num_correct = len(correct_answer)

    question_number = exam_session['current_question'] + 1
    answer_key = f"answered_{question_number}"

    if num_correct > 1:
        st.info(f"This question requires selecting {num_correct} answers.")
        new_selected_options = []
        for key in option_keys:
            checkbox_id = f"{question['question_number']}_{key}"
            checked = key in selected_options
            option_text = f"{key}. {options[key]}"
            if st.checkbox(option_text, key=checkbox_id, value=checked):
                new_selected_options.append(key)

        # Provide feedback if the user has selected the required number of options
        if len(new_selected_options) == num_correct:
            if set(new_selected_options) == set(correct_answer):
                st.success("Correct!")
            else:
                st.error("Incorrect.")
                st.markdown("**Correct answer(s):**")
                for opt in correct_answer:
                    st.markdown(f"- **{opt}. {question['options'].get(opt, 'Option not found')}**")
            exam_session['answers'][question_number] = new_selected_options
            exam_session['answered_questions'].add(question_number)
    else:
        st.info("This question requires selecting 1 answer.")

        # Check if the question has been answered
        if question_number in exam_session['answered_questions']:
            # Display options with feedback
            for key in option_keys:
                option_text = f"{key}. {options[key]}"
                if key == correct_answer[0]:
                    color = '#d4edda'  # Light green for correct
                elif key == selected_options[0]:
                    color = '#f8d7da'  # Light red for incorrect selection
                else:
                    color = None
                if color:
                    st.markdown(highlight_text(option_text, color), unsafe_allow_html=True)
                else:
                    st.write(option_text)
        else:
            # Display options as buttons
            for key in option_keys:
                option_text = f"{key}. {options[key]}"
                if st.button(option_text, key=f"option_{question_number}_{key}"):
                    selected_option = key
                    exam_session['answers'][question_number] = [selected_option]
                    exam_session['answered_questions'].add(question_number)
                    # Provide immediate feedback
                    if selected_option == correct_answer[0]:
                        st.success("Correct!")
                    else:
                        st.error(f"Incorrect. The correct answer is {correct_answer[0]}. {options[correct_answer[0]]}")
                    st.rerun()

def display_question_map(session_state, total_questions):
    """Displays a collapsible question map."""
    with st.expander("Question Map"):
        cols = st.columns(10)
        for i, q_num in enumerate(range(1, total_questions + 1)):
            col = cols[i % 10]
            label = f"{q_num}"
            if q_num in session_state['answered_questions']:
                label += " ✅"
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
            # Convert set strings back to sets
            for ex in exam_history.values():
                ex['answered_questions'] = set(ex['answered_questions'])
            return exam_history
        except Exception as e:
            st.error(f"Error loading exam history: {e}")
            return {}
    else:
        return {}

def load_used_question_ids():
    """Loads the set of used question IDs."""
    if os.path.exists('used_questions.json'):
        try:
            with open('used_questions.json', 'r', encoding='utf-8') as f:
                used_question_ids = set(json.load(f))
            return used_question_ids
        except Exception as e:
            st.error(f"Error loading used questions: {e}")
            return set()
    else:
        return set()

def save_used_question_ids(used_question_ids):
    """Saves the set of used question IDs."""
    try:
        with open('used_questions.json', 'w', encoding='utf-8') as f:
            json.dump(list(used_question_ids), f)
    except Exception as e:
        st.error(f"Error saving used questions: {e}")

def main():
    st.title("Practice Exam Simulator")

    # Load exam history from file
    if 'exam_history' not in st.session_state:
        st.session_state['exam_history'] = load_exam_history()

    # Load used question IDs
    if 'used_question_ids' not in st.session_state:
        st.session_state['used_question_ids'] = load_used_question_ids()

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
    for part_name, questions in questions_by_part.items():
        for idx, question in enumerate(questions):
            if 'id' not in question:
                question['id'] = len(all_questions) + 1  # Ensure unique ID
            question['origin'] = f"{part_name}, Question {idx + 1}"  # Add origin metadata
            all_questions.append(question)


    # Ensure all questions have a unique ID
    for idx, question in enumerate(all_questions):
        if 'id' not in question:
            question['id'] = idx + 1

    total_questions_available = len(all_questions)

    # Determine remaining questions
    remaining_questions = [q for q in all_questions if q['id'] not in st.session_state['used_question_ids']]
    remaining_questions_count = len(remaining_questions)

    # Sidebar - Start New Exam
    st.sidebar.header("Start a New Practice Test")
    if remaining_questions_count == 0:
        st.sidebar.write("All questions have been used.")
        st.sidebar.write("Resetting question pool.")
        # Reset used questions
        st.session_state['used_question_ids'] = set()
        save_used_question_ids(st.session_state['used_question_ids'])
        remaining_questions = all_questions
        remaining_questions_count = len(remaining_questions)

    start_exam = st.sidebar.button("Start New Practice Test", key='start_exam')

    # Sidebar - Exam History
    st.sidebar.header("Exam History")
    if st.session_state['exam_history']:
        for eid, ex in st.session_state['exam_history'].items():
            status = 'Completed' if ex['completed'] else 'In Progress'
            if ex['completed']:
                score = f"Score: {ex['score']:.2f}%"
            else:
                score = ""
            if st.sidebar.button(f"{eid} ({status}) {score}", key=f"history_{eid}"):
                st.session_state['current_exam'] = eid
                st.rerun()
    else:
        st.sidebar.write("No exams taken yet.")

    # Handle starting a new exam
    if start_exam:
        # Determine number of questions for the exam
        if remaining_questions_count >= 65:
            exam_questions = random.sample(remaining_questions, 65)
        else:
            exam_questions = remaining_questions
            st.warning(f"Only {remaining_questions_count} questions remaining. This exam will have {remaining_questions_count} questions.")

        # Assign sequential question numbers
        for idx, question in enumerate(exam_questions):
            question['question_number'] = idx + 1

        # Update used questions
        st.session_state['used_question_ids'].update(q['id'] for q in exam_questions)
        save_used_question_ids(st.session_state['used_question_ids'])

        exam_id = f"Exam_{len(st.session_state['exam_history']) + 1}"
        exam_session = {
            'exam_id': exam_id,
            'questions': exam_questions,
            'current_question': 0,
            'answers': {},
            'answered_questions': set(),
            'completed': False,
            'score': None,
        }
        # Save the exam to history
        st.session_state['exam_history'][exam_id] = exam_session
        st.session_state['current_exam'] = exam_id
        save_exam_history(st.session_state['exam_history'])  # Save to file
        st.rerun()

    # Display the current exam if one is active
    if 'current_exam' in st.session_state:
        exam_session = st.session_state['exam_history'][st.session_state['current_exam']]
        display_exam_interface(exam_session)
    else:
        st.write("Click 'Start New Practice Test' in the sidebar to begin.")

def display_navigation_controls(exam, total_questions):
    """Displays navigation controls for the exam."""
    current_question_index = exam['current_question']
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    # Back Button
    if col1.button("Previous", key="prev"):
        if current_question_index > 0:
            exam['current_question'] -= 1
            st.experimental_rerun()
    
    # Next Button
    if col3.button("Next", key="next"):
        if current_question_index < total_questions - 1:
            exam['current_question'] += 1
            st.experimental_rerun()

    # Display Progress
    col2.markdown(
        f"<div style='text-align: center; font-weight: bold;'>"
        f"Question {current_question_index + 1} of {total_questions}"
        f"</div>", 
        unsafe_allow_html=True
    )

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

    # Get selected options
    selected_options = exam['answers'].get(question_number, [])
    display_question(exam_session, question, selected_options)

    # Navigation controls
    display_navigation_controls(exam, total_questions)

    # Check if all questions have been answered
    if len(exam['answered_questions']) == total_questions and not exam['completed']:
        if st.button("Submit Exam"):
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
