from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()

# Get API keys and provider selection
openai_api_key = os.getenv("OPENAI_API")
google_api_key = os.getenv("GOOGLE_API_KEY")
llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()  # Default to openai

# Validate that at least one API key is available
if llm_provider == "openai" and not openai_api_key:
    raise ValueError(
        "OPENAI_API key not found. Set it in .env file or switch to gemini."
    )
elif llm_provider == "gemini" and not google_api_key:
    raise ValueError(
        "GOOGLE_API_KEY not found. Set it in .env file or switch to openai."
    )

print(f"Using LLM Provider: {llm_provider.upper()}")


class JSONResponse(BaseModel):
    """
    The response should strictly follow the following structure: -
     [
        {
        start: "Start time of the clip",
        content: "Highlight Text",
        end: "End Time for the highlighted clip"
        }
     ]
    """

    start: float = Field(description="Start time of the clip")
    content: str = Field(description="Highlight Text")
    end: float = Field(description="End time for the highlighted clip")


def get_system_prompt(num_highlights=1):
    if num_highlights == 1:
        return """
The input contains a timestamped transcription of a video.
Select a 2-minute segment from the transcription that contains something interesting, useful, surprising, controversial, or thought-provoking.
The selected text should contain only complete sentences.
Do not cut the sentences in the middle.
The selected text should form a complete thought.
Return a JSON object with the following structure:
## Output 
[{{
    start: "Start time of the segment in seconds (number)",
    content: "The transcribed text from the selected segment (clean text only, NO timestamps)",
    end: "End time of the segment in seconds (number)"
}}]

## Input
{{Transcription}}
"""
    else:
        # Use string concatenation to avoid f-string issues with {Transcription}
        return f"""
The input contains a timestamped transcription of a video.
Select {num_highlights} DIFFERENT 2-minute segments from the transcription, each containing something interesting, useful, surprising, controversial, or thought-provoking.

IMPORTANT REQUIREMENTS:
- Each segment must be COMPLETELY DIFFERENT from the others (no overlapping time ranges)
- Segments should NOT overlap in content or time
- Each segment should be around 2 minutes (60-150 seconds)
- Select the BEST {num_highlights} distinct moments from the video
- The selected text should contain only complete sentences
- Do not cut sentences in the middle
- Each segment should form a complete thought

Return a JSON array with {num_highlights} objects, each with this structure:
## Output 
[{{{{
    start: "Start time of the segment in seconds (number)",
    content: "The transcribed text from the selected segment (clean text only, NO timestamps)",
    end: "End time of the segment in seconds (number)"
}}}}]

## Input
{{{{Transcription}}}}
"""


system = get_system_prompt(1)  # Default for backward compatibility

# User = """
# Example
# """


def GetHighlight(Transcription):
    from langchain_core.prompts import ChatPromptTemplate

    try:
        # Initialize LLM based on provider
        if llm_provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model="models/gemini-2.5-flash",  # Fast and free tier available
                temperature=1.0,
                google_api_key=google_api_key,
            )
            print("Using Gemini 2.5 Flash model...")
        else:  # openai
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model="gpt-4o-mini",  # Much cheaper than gpt-4o
                temperature=1.0,
                api_key=openai_api_key,
            )
            print("Using OpenAI GPT-4o-mini model...")

        prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("user", Transcription)]
        )
        chain = prompt | llm.with_structured_output(
            JSONResponse, method="function_calling"
        )

        print("Calling LLM for highlight selection...")
        response = chain.invoke({"Transcription": Transcription})

        # Validate response
        if not response:
            print("ERROR: LLM returned empty response")
            return None, None

        if not hasattr(response, "start") or not hasattr(response, "end"):
            print(f"ERROR: Invalid response structure: {response}")
            return None, None

        try:
            Start = int(response.start)
            End = int(response.end)
        except (ValueError, TypeError) as e:
            print(f"ERROR: Could not parse start/end times from response")
            print(f"  response.start: {response.start}")
            print(f"  response.end: {response.end}")
            print(f"  Error: {e}")
            return None, None

        # Validate times
        if Start < 0 or End < 0:
            print(f"ERROR: Negative time values - Start: {Start}s, End: {End}s")
            return None, None

        if End <= Start:
            print(
                f"ERROR: Invalid time range - Start: {Start}s, End: {End}s (end must be > start)"
            )
            return None, None

        # Log the selected segment
        print(f"\n{'='*60}")
        print(f"SELECTED SEGMENT DETAILS:")
        print(f"Time: {Start}s - {End}s ({End-Start}s duration)")
        print(f"Content: {response.content}")
        print(f"{'='*60}\n")

        if Start == End:
            Ask = input("Error - Get Highlights again (y/n) -> ").lower()
            if Ask == "y":
                Start, End = GetHighlight(Transcription)
            return Start, End
        return Start, End

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetHighlight FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"\nTranscription length: {len(Transcription)} characters")
        print(f"First 200 chars: {Transcription[:200]}...")
        print(f"{'='*60}\n")
        import traceback

        traceback.print_exc()
        return None, None


def GetMultipleHighlights(Transcription, num_highlights=1):
    """
    Get multiple highlight segments from a transcription.

    Args:
        Transcription: Timestamped transcription text
        num_highlights: Number of highlights to extract

    Returns:
        List of tuples [(start1, end1), (start2, end2), ...] or None if failed
    """
    from langchain_core.prompts import ChatPromptTemplate
    from pydantic import BaseModel, Field
    from typing import List

    if num_highlights == 1:
        # Use the original function for single highlight
        start, end = GetHighlight(Transcription)
        if start is not None and end is not None:
            return [(start, end)]
        return None

    # Define response model for multiple highlights
    class MultipleHighlightsResponse(BaseModel):
        highlights: List[JSONResponse] = Field(
            description=f"List of {num_highlights} distinct highlight segments"
        )

    try:
        # Initialize LLM based on provider
        if llm_provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model="models/gemini-2.5-flash",
                temperature=1.0,
                google_api_key=google_api_key,
            )
            print(
                f"Using Gemini 2.5 Flash model to generate {num_highlights} shorts..."
            )
        else:  # openai
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=1.0,
                api_key=openai_api_key,
            )
            print(
                f"Using OpenAI GPT-4o-mini model to generate {num_highlights} shorts..."
            )

        # Use dynamic system prompt based on number of highlights
        dynamic_system = get_system_prompt(num_highlights)

        prompt = ChatPromptTemplate.from_messages(
            [("system", dynamic_system), ("user", Transcription)]
        )
        chain = prompt | llm.with_structured_output(
            MultipleHighlightsResponse, method="function_calling"
        )

        print(f"Calling LLM to select {num_highlights} highlight segments...")
        response = chain.invoke({"Transcription": Transcription})

        # Validate response
        if not response or not hasattr(response, "highlights"):
            print("ERROR: LLM returned invalid response")
            return None

        highlights = response.highlights

        if len(highlights) < num_highlights:
            print(
                f"WARNING: Only received {len(highlights)} highlights instead of {num_highlights}"
            )

        # Process and validate each highlight
        result = []
        for i, highlight in enumerate(highlights, 1):
            try:
                start = int(highlight.start)
                end = int(highlight.end)

                # Validate times
                if start < 0 or end < 0:
                    print(f"WARNING: Highlight {i} has negative time values, skipping")
                    continue

                if end <= start:
                    print(f"WARNING: Highlight {i} has invalid time range, skipping")
                    continue

                # Log the selected segment
                print(f"\n{'='*60}")
                print(f"HIGHLIGHT {i}/{num_highlights}:")
                print(f"Time: {start}s - {end}s ({end-start}s duration)")
                print(f"Content preview: {highlight.content[:100]}...")
                print(f"{'='*60}\n")

                result.append((start, end))

            except (ValueError, TypeError) as e:
                print(f"ERROR: Could not parse highlight {i}: {e}")
                continue

        if len(result) == 0:
            print("ERROR: No valid highlights could be extracted")
            return None

        return result

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR IN GetMultipleHighlights FUNCTION:")
        print(f"{'='*60}")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print(f"\nTranscription length: {len(Transcription)} characters")
        print(f"{'='*60}\n")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    print(GetHighlight(User))
