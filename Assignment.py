import argparse
import csv
import logging
from typing import List, Dict
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for the PubMed API
PUBMED_API_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# Function to fetch PubMed IDs based on a query
def fetch_pubmed_ids(query: str) -> List[str]:
    logger.info(f"Fetching PubMed IDs for query: {query}")
    response = requests.get(
        PUBMED_API_BASE_URL,
        params={"db": "pubmed", "term": query, "retmode": "json", "retmax": 100},
    )
    response.raise_for_status()
    data = response.json()
    return data.get("esearchresult", {}).get("idlist", [])

# Function to identify non-academic authors based on affiliations
def identify_non_academic_authors(authors: List[Dict]) -> List[str]:
    non_academic_authors = []
    for author in authors:
        affiliation = author.get("affiliation", "").lower()
        if affiliation and not any(keyword in affiliation for keyword in ["university", "institute", "college", "academy"]):
            non_academic_authors.append(author.get("name", "Unknown"))
    return non_academic_authors

# Function to fetch details of papers by PubMed IDs
def fetch_paper_details(pubmed_ids: List[str]) -> List[Dict]:
    logger.info(f"Fetching details for PubMed IDs: {pubmed_ids}")
    if not pubmed_ids:
        logger.warning("No PubMed IDs provided for fetching details.")
        return []

    response = requests.get(
        PUBMED_SUMMARY_URL,
        params={"db": "pubmed", "id": ",".join(pubmed_ids), "retmode": "json"},
    )
    response.raise_for_status()
    data = response.json()
    papers = []
    for uid, details in data.get("result", {}).items():
        if uid == data.get("result", {}).get("uids"):
            continue
        authors = details.get("authors", [])
        non_academic_authors = identify_non_academic_authors(authors)
        papers.append({
            "PubmedID": uid,
            "Title": details.get("title"),
            "Publication Date": details.get("pubdate"),
            "Non-academic Author(s)": ", ".join(non_academic_authors) if non_academic_authors else "N/A",
            "Company Affiliation(s)": "N/A",  # Placeholder for further extraction
            "Corresponding Author Email": "N/A",  # Placeholder for further extraction
        })
    return papers

# Function to save the paper details to a CSV file
def save_to_csv(filename: str, papers: List[Dict]):
    logger.info(f"Saving results to {filename}")
    with open(filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=[
                "PubmedID",
                "Title",
                "Publication Date",
                "Non-academic Author(s)",
                "Company Affiliation(s)",
                "Corresponding Author Email",
            ]
        )
        writer.writeheader()
        writer.writerows(papers)

# Main function for the command-line program
def main():
    parser = argparse.ArgumentParser(description="Fetch research papers from PubMed.")
    parser.add_argument("query", help="Search query for PubMed.")
    parser.add_argument("-f", "--file", help="Filename to save the results.", default=None)
    parser.add_argument("-d", "--debug", help="Enable debug mode.", action="store_true")

    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 2:  # Argument parsing error
            parser.print_help()
            logger.error("Error parsing arguments. Please check your input.")
        raise

    if args.debug:
        logger.setLevel(logging.DEBUG)

    pubmed_ids = fetch_pubmed_ids(args.query)
    if not pubmed_ids:
        logger.info("No PubMed IDs found for the given query.")
        return

    papers = fetch_paper_details(pubmed_ids)
    if not papers:
        logger.info("No paper details could be fetched.")
        return

    if args.file:
        save_to_csv(args.file, papers)
    else:
        for paper in papers:
            print(paper)

if __name__ == "__main__":
    main()
