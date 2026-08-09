from crewai import Crew


def run_crew(agent, task):

    crew = Crew(

        agents=[agent],

        tasks=[task],

        verbose=True

    )


    result = crew.kickoff()

    return result