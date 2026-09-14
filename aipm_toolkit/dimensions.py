DIMENSION_KEYS = (
    "conversational",
    "specialization",
    "autonomy",
    "accessibility",
    "explainability",
)

DEFAULT_DIMENSIONS = (
    {
        "key": "conversational",
        "title": "Conversational interaction",
        "explanation": "How open-ended and conversational the intended interaction is.",
        "low_anchor": "Guided",
        "high_anchor": "Free/open-ended",
        "midpoint": "Some guided choices with room for natural language",
    },
    {
        "key": "specialization",
        "title": "Specialization",
        "explanation": "How focused the product is on a particular task or domain.",
        "low_anchor": "General",
        "high_anchor": "Specialized",
        "midpoint": "A broad product with a clearly emphasized use case",
    },
    {
        "key": "autonomy",
        "title": "Autonomy",
        "explanation": "How much action the product can take without step-by-step user direction. 5 is theoretical, not a target.",
        "low_anchor": "Consulting",
        "high_anchor": "Full trust and autonomous agency",
        "midpoint": "Recommends or prepares actions for user approval",
    },
    {
        "key": "accessibility",
        "title": "Accessibility / audience breadth",
        "explanation": "How broadly the intended product experience can be used. Broad reach does not establish accessibility for every user.",
        "low_anchor": "Niche",
        "high_anchor": "Broadly accessible/usable",
        "midpoint": "Usable by a wider audience with some constraints",
    },
    {
        "key": "explainability",
        "title": "Explainability",
        "explanation": "How transparent the visible product experience is, not access to reliable internal model reasoning.",
        "low_anchor": "Black box",
        "high_anchor": "Fully transparent",
        "midpoint": "Some visible explanation of inputs, outputs, or limits",
    },
)
