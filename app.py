import re
import os
import json
import streamlit as st


def navigate_to_question(part_name, question_number):
    """Sets query parameters to navigate to a specific question."""
    if part_name and question_number:
         st.experimental_set_query_params(part=part_name, question=str(question_number))
        st.stop()  # Stop further execution to allow Streamlit to rerun with updated parameters


def initialize_part_session_state(part_name, question_number=None):
    """Initializes the session state for a given part."""
    if part_name not in st.session_state:
        st.session_state[part_name] = {
            'current_question': 0 if question_number is None else question_number - 1,
            'answers': {},
        }
    else:
        if question_number is not None:
            st.session_state[part_name]['current_question'] = question_number - 1


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
            index = 0
        selected_option = st.radio(
            "Select your answer:",
            options_list,
            index=index,
            key=radio_id
        )
        selected_letter = selected_option.split('.')[0]
        return [selected_letter]


def display_navigation_controls(part_name, session_state, total_questions):
    """Displays navigation controls for the exam."""
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous", key=f"prev_{part_name}_{session_state['current_question']}"):
            if session_state['current_question'] > 0:
                session_state['current_question'] -= 1
                st.rerun()
    with col2:
        if st.button("Next", key=f"next_{part_name}_{session_state['current_question']}"):
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


def main():
    # Handle navigation from query parameters
    query_params = st.query_params
    if "part" in query_params and "question" in query_params:
        part_name = query_params.get("part")
        question_number = query_params.get("question")
        try:
            question_number = int(question_number)
            st.session_state["part_name"] = part_name
            st.session_state["current_question"] = question_number - 1
        except ValueError:
            st.error("Invalid query parameter value for 'question'")
        st.stop()  # Stop execution to reload with updated session state

    st.title("Practice Exam Simulator")

    # Handle query parameters
    query_params = st.query_params
    part_name = query_params.get("part", None)
    question_number = query_params.get("question", None)
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

    # Part selection
    st.sidebar.header("Select Part")
    selected_part = st.sidebar.selectbox("Choose a part:", parts)
    part_name = selected_part

    # Initialize session state for navigation
    initialize_part_session_state(part_name, question_number)

    session_state = st.session_state[part_name]

    # Search functionality
    st.sidebar.header("Search Questions")
    search_query = st.sidebar.text_input("Enter a keyword or phrase to search:")
    st.session_state["search_query"] = search_query

    if search_query:
        if st.sidebar.button("Return to Exam"):
            st.session_state["search_query"] = ""
             st.experimental_set_query_params()
            st.rerun()

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
                    search_results.append({
                        'part_name': part_name_search,
                        'question_number': question['question_number'],
                        'question_text': question['question_text'],
                        'options': question['options']
                    })

        st.sidebar.write(f"Found {len(search_results)} questions relating to '{search_query}'")
        st.sidebar.write(f"There are {total_instances} instances of '{search_query}'")

    if search_results:
        st.subheader("Search Results")
        for result in search_results:
            st.markdown(f"**Part:** {result['part_name']}, **Question {result['question_number']}**")
            st.write(result['question_text'])

            for option, option_text in result['options'].items():
                st.markdown(f"- **{option}**: {option_text}")

            if st.button(f"Go to Question {result['question_number']} in {result['part_name']}"):
                navigate_to_question(result['part_name'], result['question_number'])

            st.markdown("---")
    else:
        # Display the exam interface
        st.header(part_name)
        questions = questions_by_part[part_name]
        total_questions = len(questions)

        question = questions[session_state['current_question']]
        question_number = question['question_number']
        st.subheader(f"Question {question_number} of {total_questions}")

        # Display question map
        display_question_map(session_state, total_questions)

        # Display question and get updated selected options
        selected_options = session_state['answers'].get(question_number, [])
        new_selected_options = display_question(question, selected_options)
        session_state['answers'][question_number] = new_selected_options

        # Navigation controls
        display_navigation_controls(part_name, session_state, total_questions)

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
