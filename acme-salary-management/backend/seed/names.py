"""Fictional name pools per country (first names, last names). Purely synthetic data."""

NAMES: dict[str, tuple[list[str], list[str]]] = {
    "IN": (
        ["Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karthik", "Siddharth", "Rahul", "Vikram", "Ishaan",
         "Ananya", "Diya", "Priya", "Kavya", "Meera", "Neha", "Pooja", "Riya", "Sneha", "Tanvi",
         "Rajesh", "Suresh", "Amit", "Deepak", "Manoj", "Lakshmi", "Sunita", "Anjali", "Nikhil", "Varun"],
        ["Sharma", "Verma", "Iyer", "Nair", "Reddy", "Patel", "Gupta", "Mehta", "Kapoor", "Joshi",
         "Menon", "Rao", "Chatterjee", "Banerjee", "Das", "Singh", "Kulkarni", "Desai", "Bhatt", "Pillai",
         "Agarwal", "Malhotra", "Chopra", "Saxena", "Naidu", "Shetty", "Bose", "Mukherjee", "Trivedi", "Hegde"],
    ),
    "US": (
        ["James", "Michael", "Robert", "David", "William", "Daniel", "Matthew", "Joseph", "Andrew", "Ryan",
         "Emily", "Sarah", "Jessica", "Ashley", "Megan", "Lauren", "Rachel", "Olivia", "Hannah", "Natalie",
         "Marcus", "Tyrone", "Carlos", "Diego", "Jamal", "Brianna", "Maria", "Sofia", "Aaliyah", "Kevin"],
        ["Anderson", "Brooks", "Carter", "Davis", "Edwards", "Foster", "Garcia", "Harris", "Jackson", "Kim",
         "Lopez", "Martinez", "Nguyen", "Owens", "Parker", "Quinn", "Reed", "Sullivan", "Taylor", "Walker",
         "Young", "Bennett", "Coleman", "Dixon", "Ellis", "Fisher", "Grant", "Hughes", "Ingram", "Jenkins"],
    ),
    "DE": (
        ["Lukas", "Felix", "Jonas", "Maximilian", "Leon", "Paul", "Tim", "Niklas", "Jan", "Stefan",
         "Anna", "Lena", "Sophie", "Marie", "Laura", "Julia", "Katharina", "Hannah", "Clara", "Lea",
         "Matthias", "Andreas", "Thomas", "Sabine", "Petra", "Monika", "Jürgen", "Klaus", "Greta", "Ingrid"],
        ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Schulz", "Hoffmann",
         "Koch", "Bauer", "Richter", "Klein", "Wolf", "Schröder", "Neumann", "Schwarz", "Zimmermann", "Braun",
         "Krüger", "Hofmann", "Hartmann", "Lange", "Werner", "Krause", "Lehmann", "Köhler", "Maier", "Fuchs"],
    ),
    "GB": (
        ["Oliver", "George", "Harry", "Jack", "Charlie", "Thomas", "Oscar", "Henry", "Edward", "Callum",
         "Amelia", "Isla", "Poppy", "Freya", "Charlotte", "Ruby", "Florence", "Eleanor", "Imogen", "Holly",
         "Alfie", "Archie", "Rhys", "Gareth", "Fiona", "Morag", "Siobhan", "Ffion", "Bethan", "Callie"],
        ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Evans", "Thomas", "Roberts", "Johnson",
         "Walsh", "Robinson", "Thompson", "Wright", "Walker", "White", "Edwards", "Hughes", "Green", "Hall",
         "Lewis", "Harrison", "Clarke", "Patel", "Jackson", "Wood", "Turner", "Martin", "Cooper", "Hill"],
    ),
    "SG": (
        ["Wei", "Jun", "Hao", "Kai", "Ming", "Zhi", "Jia", "Xin", "Li", "Yu",
         "Hui", "Mei", "Ling", "Shu", "Ying", "Aisha", "Nurul", "Farid", "Hakim", "Siti",
         "Arun", "Priyanka", "Kumar", "Devi", "Ravi", "Raj", "Sanjay", "Kavitha", "Ethan", "Chloe"],
        ["Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh",
         "Teo", "Ang", "Yeo", "Sim", "Chong", "Abdullah", "Rahman", "Ismail", "Hassan", "Yusof",
         "Pillay", "Nair", "Krishnan", "Subramaniam", "Chew", "Low", "Toh", "Foo", "Heng", "Seah"],
    ),
    "CA": (
        ["Liam", "Noah", "Ethan", "Lucas", "Benjamin", "Jacob", "Nathan", "Mason", "Logan", "Owen",
         "Emma", "Chloé", "Léa", "Mia", "Zoe", "Avery", "Madison", "Brooke", "Claire", "Sydney",
         "Étienne", "Mathieu", "Jean-Luc", "Amrit", "Harpreet", "Gurpreet", "Jasmine", "Kiran", "Dylan", "Tessa"],
        ["Tremblay", "Gagnon", "Roy", "Côté", "Bouchard", "Gauthier", "Morin", "Lavoie", "Fortin", "Gagné",
         "MacDonald", "Campbell", "Stewart", "Murray", "Fraser", "Singh", "Gill", "Sandhu", "Dhillon", "Chen",
         "Wilson", "Anderson", "Clark", "Scott", "Ross", "Henderson", "Mitchell", "Reid", "Cameron", "Ferguson"],
    ),
}

DIAL_CODES = {"IN": "+91", "US": "+1", "DE": "+49", "GB": "+44", "SG": "+65", "CA": "+1"}
