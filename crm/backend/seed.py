"""Load the sample desk: python seed.py"""

from app.seed_data import seed


if __name__ == "__main__":
    created = seed()
    print("Seeded Harbor CRM." if created else "Harbor CRM already has accounts; seed skipped.")
