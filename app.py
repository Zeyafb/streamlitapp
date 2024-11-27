import re
import os
import json
import streamlit as st


def highlight_text(text, search_query):
    """Highlights the search query within the given text."""
    escaped_query = re.escape(search_query)
    highlighted_text = re.sub(
        f"({escaped_query})",
        r"<span style='background-color: #f3f3f3; color: #333; padding: 2px; border-radius: 4px;'>\1</span>",
        text,
        flags=re.IGNORECASE
    )
    return highlighted_text

def highlight_text(text, search_query):
    """Highlights the search query within the given text."""
    escaped_query = re.escape(search_query)
    highlighted_text = re.sub(
        f"({escaped_query})",
        r"<span style='background-color: #f3f3f3; color: #333; padding: 2px; border-radius: 4px;'>\1</span>",
        text,
        flags=re.IGNORECASE
    )
    return highlighted_text

def navigate_to_question(part_name, question_number):
    """Sets query parameters to navigate to a specific question."""
    st.experimental_set_query_params(part=part_name, question=question_number)
    st.rerun()


def initialize_part_session_state(part_name, question_number=None):
    """Initializes the session state for a given part."""
    if part_name not in st.session_state:
        st.session_state[part_name] = {
            'current_question': 0 if question_number is None else question_number - 1,
            'answers': {},
            'show_results': False,
            'flagged': set()
        }
    else:
        if question_number is not None:
            st.session_state[part_name]['current_question'] = question_number - 1
        if 'flagged' not in st.session_state[part_name]:
            st.session_state[part_name]['flagged'] = set()


def display_question(question, selected_options, part_name, session_state):
    """Displays the question and options, with optional search query highlighting."""
    st.write("---")
    
    # Check if there is an active search query
    search_query = st.session_state.get("search_query", "")
    
    # Highlight the question text
    question_text = question['question_text']
    if search_query:
        question_text = highlight_text(question_text, search_query)
    st.markdown(question_text, unsafe_allow_html=True)

    # Display options with highlighting
    options = question['options']
    option_keys = list(options.keys())
    correct_answer = question.get('correct_answer', [])
    num_correct = len(correct_answer)

    if num_correct > 1:
        st.info(f"This question requires selecting {num_correct} answers.")
        new_selected_options = []
        for key in option_keys:
            checkbox_id = f"{part_name}_{session_state['current_question']}_{key}"
            option_text = options[key]
            if search_query:
                option_text = highlight_text(option_text, search_query)
            checked = key in selected_options
            if st.checkbox(f"{key}. {option_text}", key=checkbox_id, value=checked):
                new_selected_options.append(key)
        return new_selected_options
    else:
        st.info("This question requires selecting 1 answer.")
        radio_id = f"{part_name}_{session_state['current_question']}"
        options_list = [f"{key}. {highlight_text(options[key], search_query) if search_query else options[key]}" for key in option_keys]
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
    col1, col2, col3 = st.columns(3)
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
    with col3:
        if st.button("Submit Exam", key=f"submit_{part_name}"):
            session_state['show_results'] = True
            st.rerun()


def display_question_map(part_name, session_state, total_questions):
    """Displays a collapsible question map."""
    with st.expander("Question Map"):
        cols = st.columns(10)
        for i, q_num in enumerate(range(1, total_questions + 1)):
            col = cols[i % 10]
            label = f"{q_num}"
            if q_num in session_state['flagged']:
                label += " ⚑"
            if col.button(label, key=f"qmap_{part_name}_{q_num}"):
                session_state['current_question'] = q_num - 1
                st.rerun()


def display_exam_results(questions, session_state):
    """Displays the exam results."""
    correct_answers_count = 0
    total_questions = len(questions)
    for question in questions:
        question_number = question['question_number']
        st.subheader(f"Question {question_number}")
        st.write(question['question_text'])

        options = question['options']
        selected_options = session_state['answers'].get(question_number, [])
        correct_options = question.get('correct_answer', [])
        is_correct = set(selected_options) == set(correct_options)

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

    percentage_score = (correct_answers_count / total_questions) * 100
    st.write(f"Your total score: {correct_answers_count} out of {total_questions} ({percentage_score:.2f}%)")

    if st.button("Retake Exam"):
        session_state['current_question'] = 0
        session_state['answers'] = {}
        session_state['show_results'] = False
        session_state['flagged'] = set()
        st.rerun()


def main():
    st.title("Practice Exam Simulator")

    # Handle query parameters
    query_params = st.experimental_get_query_params()
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
    st.session_state["mode"] = mode

    # Initialize session state for navigation
    if part_name and question_number is not None:
        initialize_part_session_state(part_name, question_number)
    else:
        for part in parts:
            initialize_part_session_state(part)

    # Search functionality in the sidebar
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
            st.markdown(f"**Part:** {result['part_name']}, **Question {result['question_number']}**")
            
            # Highlight the question text
            st.markdown(result['question_text'], unsafe_allow_html=True)
    
            # Highlight options
            for option, option_text in result['options'].items():
                st.markdown(f"- **{option}**: {option_text}", unsafe_allow_html=True)
    
            if st.button(f"Go to Question {result['question_number']} in {result['part_name']}",
                         key=f"nav_{result['part_name']}_{result['question_number']}"):
                navigate_to_question(result['part_name'], result['question_number'])
    
            st.markdown("---")


    # Display flagged questions
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

            # Ensure session state is properly initialized for the current part
            initialize_part_session_state(part_name_tab)
            
            session_state = st.session_state[part_name_tab]
            
            if not session_state.get('show_results', False):  # Safely access 'show_results' with a default value
                question = questions[session_state['current_question']]
                question_number = question['question_number']
                is_flagged = question_number in session_state['flagged']
                flag_label = " ⚑" if is_flagged else ""
                st.subheader(f"Question {question_number} of {total_questions}{flag_label}")
            
                # Display question map
                display_question_map(part_name_tab, session_state, total_questions)
            
                # Display question and get updated selected options
                selected_options = session_state['answers'].get(question_number, [])
                new_selected_options = display_question(question, selected_options, part_name_tab, session_state)
                session_state['answers'][question_number] = new_selected_options
            
                # Flagging option
                if st.checkbox("Flag this question", value=is_flagged, key=f"flag_{part_name_tab}_{question_number}"):
                    session_state['flagged'].add(question_number)
                else:
                    session_state['flagged'].discard(question_number)
            
                # Navigation controls
                display_navigation_controls(part_name_tab, session_state, total_questions)
            
                # Behavior based on mode
                if st.session_state["mode"] == "Practice Mode":
                    if st.button("Check Answer", key=f"check_{part_name_tab}_{session_state['current_question']}"):
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
            else:
                st.header("Exam Results")
                display_exam_results(questions, session_state)



if __name__ == "__main__":
    main()
