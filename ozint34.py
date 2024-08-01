import requests
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import json
import csv
import webbrowser
from bs4 import BeautifulSoup
from PIL import Image
from PIL.ExifTags import TAGS
import os

def get_country_from_coordinates(lat, lon):
    """Use OpenStreetMap's Nominatim for reverse geocoding."""
    try:
        url = 'https://nominatim.openstreetmap.org/reverse'
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'YourAppName/1.0 (your-email@example.com)'  # Replace with your app name and contact
        }
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        
        data = response.json()
        if 'address' in data:
            address = data['address']
            country = address.get('country')
            return country
        else:
            messagebox.showerror("Error", "No address information found for the coordinates.")
            return None
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Request error: {e}")
        return None
    except ValueError as e:
        messagebox.showerror("Error", f"Error parsing JSON response: {e}")
        return None

def extract_metadata_from_image(image_path):
    """Extract metadata from an image, including GPS coordinates."""
    try:
        image = Image.open(image_path)
        info_dict = {
            "Image Size": f"{image.size[0]} x {image.size[1]}",
            "Image Height": image.height,
            "Image Width": image.width,
            "Image Format": image.format,
            "Image Mode": image.mode
        }
        exif_data = image._getexif()
        if exif_data:
            gps_info = None
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                info_dict[tag_name] = value
                if tag_name == 'GPSInfo':
                    gps_info = value
                    try:
                        lat = gps_info.get(2, [0, 0, 0])
                        lon = gps_info.get(4, [0, 0, 0])
                        lat = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / 3600
                        lon = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / 3600
                        if gps_info.get(3) == 'S':
                            lat = -lat
                        if gps_info.get(1) == 'W':
                            lon = -lon
                        info_dict['GPS Latitude'] = lat
                        info_dict['GPS Longitude'] = lon
                        # Also find country from coordinates
                        country = get_country_from_coordinates(lat, lon)
                        if country:
                            info_dict["Country"] = country
                    except (TypeError, ValueError) as e:
                        info_dict['GPS Latitude'] = 'Invalid data'
                        info_dict['GPS Longitude'] = 'Invalid data'
                        messagebox.showerror("Error", f"Error processing GPS data: {e}")
            if not gps_info:
                info_dict['GPS Latitude'] = 'Not available'
                info_dict['GPS Longitude'] = 'Not available'
        return info_dict
    except Exception as e:
        messagebox.showerror("Error", f"Error extracting metadata: {e}")
        return {}

def scrape_lovinmalta(person_name, city, country, keywords):
    query = f"{person_name} {city} {country} {keywords}".strip().replace(' ', '+')
    search_url = f'https://lovinmalta.com/search/{query}'
    response = requests.get(search_url)
    articles = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.select('.entry-title a'):
            title = item.get_text()
            url = item['href']
            articles.append({'title': title, 'url': url, 'source': 'Lovin Malta'})
    return articles

def scrape_timesofmalta(person_name, city, country, keywords):
    query = f"{person_name} {city} {country} {keywords}".strip().replace(' ', '+')
    search_url = f'https://timesofmalta.com/search?q={query}'
    response = requests.get(search_url)
    articles = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.select('.article-title a'):
            title = item.get_text()
            url = item['href']
            articles.append({'title': title, 'url': url, 'source': 'Times of Malta'})
    return articles

def get_news_about_person(person_name, city, country, keywords, api_key):
    url = 'https://newsapi.org/v2/everything'
    query = f"{person_name} {keywords} {city} {country}".strip().replace(' ', '+')
    params = {
        'q': query,
        'apiKey': api_key,
        'language': 'en',
        'sortBy': 'relevancy',
        'pageSize': 10
    }

    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('articles', [])
    elif response.status_code == 401:
        messagebox.showerror("Error", "Unauthorized request: Check your API key.")
    else:
        messagebox.showerror("Error", f"Error fetching news: {response.status_code}")
    
    return []

def search_with_metadata(person_name, city, country, keywords):
    news_api_key = news_api_key_entry.get()
    # Get news articles from NewsAPI
    api_articles = get_news_about_person(person_name, city, country, keywords, news_api_key)
    
    # Scrape news articles from Lovin Malta and Times of Malta
    lovinmalta_articles = scrape_lovinmalta(person_name, city, country, keywords)
    timesofmalta_articles = scrape_timesofmalta(person_name, city, country, keywords)
    
    # Combine all articles
    all_articles = api_articles + lovinmalta_articles + timesofmalta_articles
    
    # Display articles
    display_articles(all_articles)
    
    # Enable the save button if articles are found
    save_button.config(state=tk.NORMAL if all_articles else tk.DISABLED)

def search():
    person_name = name_entry.get()
    city = city_entry.get()
    country = country_entry.get()
    keywords = keywords_entry.get()
    
    if person_name or city or country or keywords:
        search_with_metadata(person_name, city, country, keywords)
    else:
        messagebox.showerror("Input Error", "Please provide at least one search criterion.")

def open_url(event):
    webbrowser.open_new(event.widget.cget("text"))

def display_articles(articles):
    global displayed_articles
    displayed_articles = articles
    for widget in results_frame.winfo_children():
        widget.destroy()
        
    if articles:
        for i, article in enumerate(articles, start=1):
            title = article.get('title', 'No Title')
            description = article.get('description', 'No Description')
            url = article['url']
            source = article.get('source', 'Unknown Source')
            
            tk.Label(results_frame, text=f"Article {i} ({source}):", font=('Helvetica', 14, 'bold')).pack(anchor='w')
            tk.Label(results_frame, text=f"Title: {title}", font=('Helvetica', 12)).pack(anchor='w')
            tk.Label(results_frame, text=f"Description: {description}", font=('Helvetica', 12)).pack(anchor='w')
            link = tk.Label(results_frame, text=url, font=('Helvetica', 12, 'underline'), fg='blue', cursor="hand2")
            link.pack(anchor='w')
            link.bind("<Button-1>", open_url)
            tk.Label(results_frame, text="-"*80).pack(anchor='w')
    else:
        tk.Label(results_frame, text="No articles found.", font=('Helvetica', 12)).pack(anchor='w')

def save_articles(articles):
    if not articles:
        messagebox.showinfo("No Articles", "There are no articles to save.")
        return
    
    filetypes = [("JSON files", "*.json"), ("CSV files", "*.csv")]
    file_path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=filetypes)
    
    if file_path:
        if file_path.endswith('.json'):
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(articles, json_file, ensure_ascii=False, indent=4)
        elif file_path.endswith('.csv'):
            with open(file_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["source", "author", "title", "description", "url", "publishedAt", "content"])
                writer.writeheader()
                for article in articles:
                    writer.writerow({
                        "source": article.get('source'),
                        "author": article.get('author'),
                        "title": article.get('title'),
                        "description": article.get('description'),
                        "url": article.get('url'),
                        "publishedAt": article.get('publishedAt'),
                        "content": article.get('content'),
                    })
        messagebox.showinfo("Success", "Results saved successfully.")

def on_drop(event):
    image_path = event.data
    if os.path.isfile(image_path) and image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        # Display image path
        metadata = extract_metadata_from_image(image_path)
        metadata_text = "\n".join([f"{key}: {value}" for key, value in metadata.items()])
        metadata_display.config(state=tk.NORMAL)
        metadata_display.delete(1.0, tk.END)
        metadata_display.insert(tk.END, metadata_text)
        metadata_display.config(state=tk.DISABLED)
        
        # Extract relevant fields from metadata for searching
        person_name = metadata.get("Artist", "")
        city = metadata.get("City", "")
        country = metadata.get("Country", "")
        keywords = metadata.get("Keywords", "")
        
        # Fill fields
        name_entry.delete(0, tk.END)
        name_entry.insert(0, person_name)
        city_entry.delete(0, tk.END)
        city_entry.insert(0, city)
        country_entry.delete(0, tk.END)
        country_entry.insert(0, country)
        keywords_entry.delete(0, tk.END)
        keywords_entry.insert(0, keywords)
        
        search_with_metadata(person_name, city, country, keywords)
    else:
        messagebox.showerror("Error", "Invalid file format or file not found.")

# Setup the GUI
root = TkinterDnD.Tk()
root.title("News Search")

# Frame for main content
main_frame = tk.Frame(root)
main_frame.grid(row=0, column=0, sticky='nsew')

# Setup grid weights
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
main_frame.grid_rowconfigure(1, weight=1)
main_frame.grid_columnconfigure(0, weight=1)
main_frame.grid_columnconfigure(1, weight=1)

# Add content to the main frame
tk.Label(main_frame, text="News API Key:").grid(row=0, column=0, padx=10, pady=5, sticky='w')
news_api_key_entry = tk.Entry(main_frame, width=30)
news_api_key_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(main_frame, text="Name:").grid(row=1, column=0, padx=10, pady=5, sticky='w')
name_entry = tk.Entry(main_frame, width=30)
name_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Label(main_frame, text="City:").grid(row=2, column=0, padx=10, pady=5, sticky='w')
city_entry = tk.Entry(main_frame, width=30)
city_entry.grid(row=2, column=1, padx=10, pady=5)

tk.Label(main_frame, text="Country:").grid(row=3, column=0, padx=10, pady=5, sticky='w')
country_entry = tk.Entry(main_frame, width=30)
country_entry.grid(row=3, column=1, padx=10, pady=5)

tk.Label(main_frame, text="Keywords:").grid(row=4, column=0, padx=10, pady=5, sticky='w')
keywords_entry = tk.Entry(main_frame, width=30)
keywords_entry.grid(row=4, column=1, padx=10, pady=5)

tk.Button(main_frame, text="Search", command=search).grid(row=5, column=0, columnspan=2, padx=10, pady=10)

# Create a drop target area
drop_area = tk.Label(main_frame, text="Drag and Drop an Image Here", relief=tk.RAISED, padx=20, pady=20)
drop_area.grid(row=6, column=0, columnspan=2, padx=10, pady=10)
drop_area.drop_target_register(DND_FILES)
drop_area.dnd_bind('<<Drop>>', on_drop)

metadata_display = tk.Text(main_frame, height=10, width=80, wrap=tk.WORD, state=tk.DISABLED)
metadata_display.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

save_button = tk.Button(main_frame, text="Save Results", command=lambda: save_articles(displayed_articles), state=tk.DISABLED)
save_button.grid(row=8, column=0, columnspan=2, padx=10, pady=10)

# Frame for displaying results with scroll functionality
results_canvas = tk.Canvas(main_frame, width=800, height=400)
results_canvas.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky='nsew')

scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=results_canvas.yview)
scrollbar.grid(row=9, column=2, sticky='ns')

results_frame = tk.Frame(results_canvas)
results_frame.bind(
    "<Configure>",
    lambda e: results_canvas.configure(
        scrollregion=results_canvas.bbox("all")
    )
)

results_canvas.create_window((0, 0), window=results_frame, anchor="nw")
results_canvas.configure(yscrollcommand=scrollbar.set)

displayed_articles = []

root.mainloop()
