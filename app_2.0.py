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
    st.markdown(f"<div style='text-align: left; font-size: 18px;'>{question_text}</div>", unsafe_allow_html=True)

    # Display the origin of the question
    question_origin_html = f"<div style='text-align: left; font-style: italic;'>Source: {question['origin']}</div>"
    st.markdown(question_origin_html, unsafe_allow_html=True)

    # Display the options
    options = question['options']
    correct_answer = question.get('correct_answer', [])
    num_correct = len(correct_answer)
    question_number = exam_session['current_question'] + 1

    # Inject CSS for single-answer questions
    if num_correct == 1:
        st.markdown(
            """
            <style>
            div.stButton > button {
                text-align: left !important;
                display: block !important;
                margin: 5px 0 !important;
                width: 100% !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    # Inject CSS for shrinking navigation buttons
    st.markdown(
        """
        <style>
        div.navigation-button > button {
            width: auto !important;
            min-width: 100px !important;
            padding: 5px 10px !important;
            text-align: center !important;
            margin: 10px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Logic for multi-answer questions
    if num_correct > 1:
        st.info(f"This question requires selecting {num_correct} answers.")
        new_selected_options = []

        if question_number in exam_session['answers']:
            selected_options = exam_session['answers'][question_number]
            for key, value in options.items():
                option_text = f"{key}. {value}"
                if key in correct_answer and key in selected_options:
                    color = 'lightgreen'
                elif key in correct_answer:
                    color = 'lightgreen'
                elif key in selected_options:
                    color = 'salmon'
                else:
                    color = 'white'
                st.markdown(f"<div style='background-color: {color}; padding: 10px; border-radius:5px; text-align: left;'>{option_text}</div>", unsafe_allow_html=True)
            if set(selected_options) == set(correct_answer):
                st.success("Correct!")
            else:
                st.error(f"Incorrect. The correct answers are: {', '.join(correct_answer)}")
        else:
            for key, value in options.items():
                checkbox_id = f"{question_number}_{key}"
                checked = key in selected_options
                if st.checkbox(f"{key}. {value}", key=checkbox_id, value=checked):
                    if key not in new_selected_options:
                        new_selected_options.append(key)
                else:
                    if key in new_selected_options:
                        new_selected_options.remove(key)
            if st.button("Submit Answer"):
                exam_session['answers'][question_number] = new_selected_options
                exam_session['answered_questions'].add(question_number)
                if set(new_selected_options) == set(correct_answer):
                    st.success("Correct!")
                else:
                    st.error(f"Incorrect. The correct answers are: {', '.join(correct_answer)}")
                st.rerun()
    else:
        st.info("This question requires selecting 1 answer.")

        if question_number in exam_session['answers']:
            selected_option = exam_session['answers'][question_number][0]
            for key, value in options.items():
                option_text = f"{key}. {value}"
                if key in correct_answer:
                    color = 'lightgreen'
                elif key == selected_option:
                    color = 'salmon'
                else:
                    color = 'white'
                st.markdown(f"""
                    <div style='background-color: {color}; padding: 10px; border-radius:5px; text-align: left;'>
                        {option_text}
                    </div>
                """, unsafe_allow_html=True)
            if selected_option in correct_answer:
                st.success("Correct!")
            else:
                st.error(f"Incorrect. The correct answer is: {', '.join(correct_answer)}")
        else:
            # Display buttons vertically for single-answer questions
            for key, value in options.items():
                if st.button(f"{key}. {value}", key=f"option_{question_number}_{key}"):
                    selected_option = key
                    exam_session['answers'][question_number] = [selected_option]
                    exam_session['answered_questions'].add(question_number)
                    if selected_option in correct_answer:
                        st.success("Correct!")
                    else:
                        st.error(f"Incorrect. The correct answer is: {', '.join(correct_answer)}")
                    st.rerun()

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown('<div class="navigation-button">', unsafe_allow_html=True)
        st.button("Previous", key="button_previous")
    
    with col2:
        st.markdown('<div class="navigation-button">', unsafe_allow_html=True)
        st.button("Next", key="button_next")
    
    with col3:
        st.markdown('<div class="navigation-button">', unsafe_allow_html=True)
        st.button("Back to Exam List", key="button_back_to_list")





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
            if q_num in session_state['answered_questions']:
                label += " ✅"
            if col.button(label, key=f"qmap_{q_num}"):
                session_state['current_question'] = q_num - 1
                st.rerun()

def save_exam_history(exam_history):
    """Saves the exam history to a JSON file."""
    try:
        serializable_exam_history = {}
        for eid, ex in exam_history.items():
            ex_copy = ex.copy()
            # Convert 'answered_questions' set to list
            ex_copy['answered_questions'] = list(ex_copy['answered_questions'])
            serializable_exam_history[eid] = ex_copy
        with open('exam_history.json', 'w', encoding='utf-8') as f:
            json.dump(serializable_exam_history, f)
    except Exception as e:
        st.error(f"Error saving exam history: {e}")

def load_exam_history():
    """Loads the exam history from a JSON file."""
    if os.path.exists('exam_history.json'):
        try:
            with open('exam_history.json', 'r', encoding='utf-8') as f:
                exam_history = json.load(f)
            # Convert 'answered_questions' lists back to sets
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
        remaining_questions_count = len(remaining_questions)
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
                for key, value in options.items():
                    option_text = f"{key}. {value}"
                    if key in correct_answer and key in selected_options:
                        st.markdown(f"- ✅ **{option_text}**")
                    elif key in correct_answer:
                        st.markdown(f"- 🟩 **{option_text} (Correct Answer)**")
                    elif key in selected_options:
                        st.markdown(f"- ❌ {option_text}")
                    else:
                        st.markdown(f"- {option_text}")

    # Option to go back to exam list
    if st.button("Back to Exam List"):
        del st.session_state['current_exam']
        st.rerun()

if __name__ == "__main__":
    main()
