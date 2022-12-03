from dotenv import load_dotenv
import os

load_dotenv()

def main():
	print(os.environ.get("LEAFLET_BASE_URL"))

if __name__ == "__main__":
	main()