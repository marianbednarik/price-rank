import requests
from random import choice
import streamlit as st


# Headers
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": choice(
        [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        ]
    ),
}


# Function to fetch categories
def fetch_categories():
    url = "https://content.services.dmtech.com/rootpage-dm-shop-sk-sk/?view=navigation"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch categories.")
        return None


# Function to fetch filters for a category
def fetch_filters(category_link):
    url = f"https://content.services.dmtech.com/rootpage-dm-shop-sk-sk{category_link}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        for item in data.get("mainData", []):
            if item.get("type") == "DMSearchProductGrid":
                return item.get("query", {}).get("filters", "")
    else:
        st.error("Failed to fetch filters for the category.")
        return None


# Function to fetch data from the main endpoint
def fetch_data_from_category(filters, page_size=1000):
    filters = filters.replace(":", "=")
    url = f"https://product-search.services.dmtech.com/sk/search/static?{filters}&pageSize={page_size}&sort=editorial_relevance&type=search-static"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch data for filters: {filters}")
        return None


# Function to process and order products by popularity and rating using Bayesian Average
def process_products(products, include_price):
    m = 5  # minimum number of ratings required to be considered
    C = 3.5  # mean rating across all products
    price_weight = 0.01  # Adjust the weight of the price impact

    for product in products:
        R = product.get("ratingValue", 0)
        v = product.get("ratingCount", 0)
        if v > 0:
            product["popularity_score"] = round(
                (v / (v + m)) * R + (m / (v + m)) * C, 4
            )
            if include_price and "price" in product and "value" in product["price"]:
                price = product["price"]["value"]
                popularity_with_price = (
                    2
                    * product["popularity_score"]
                    * (1 / (price_weight * price))
                    / (product["popularity_score"] + (1 / (price_weight * price)))
                )
                product["popularity_score"] = round(popularity_with_price, 4)
        else:
            product["popularity_score"] = (
                0  # Ensure the key exists even if the product has no ratings
            )

    sorted_products = sorted(
        [p for p in products if p["popularity_score"] > 0],
        key=lambda x: x["popularity_score"],
        reverse=True,
    )
    return sorted_products[:25]


# Streamlit app
def main():
    st.title("Product Search and Rating")

    categories_data = fetch_categories()
    if categories_data:
        # Filter out categories with no children and excluded IDs
        main_categories = [
            c
            for c in categories_data["navigation"]["children"]
            if c.get("children")
            and c["id"] not in ["352332", "309344", "242526"]
            and not c["hidden"]
        ]

        main_category = st.selectbox(
            "Select Main Category", [c["title"] for c in main_categories]
        )
        if main_category:
            subcategories = [c for c in main_categories if c["title"] == main_category][
                0
            ]["children"]
            sub_category = st.selectbox(
                "Select Sub-Category",
                [c["title"] for c in subcategories if not c["hidden"]],
            )
            if sub_category:
                sub_subcategories = [
                    c for c in subcategories if c["title"] == sub_category
                ][0]["children"]
                sub_sub_category_titles = ["None"] + [
                    c["title"] for c in sub_subcategories if not c["hidden"]
                ]
                sub_sub_category = st.selectbox(
                    "Select Sub-Sub-Category", sub_sub_category_titles
                )

                if sub_sub_category:
                    if sub_sub_category == "None":
                        category_link = [
                            c for c in subcategories if c["title"] == sub_category
                        ][0]["link"]
                    else:
                        category_link = [
                            c
                            for c in sub_subcategories
                            if c["title"] == sub_sub_category
                        ][0]["link"]

                    filters = fetch_filters(category_link)
                    if filters:
                        include_price = st.checkbox(
                            "Include Price in Popularity Calculation"
                        )

                        if st.button("Fetch Data"):
                            data = fetch_data_from_category(filters)
                            if data:
                                products = data.get("products", [])
                                count = data.get("count", 0)

                                if count > 1000:
                                    st.warning(
                                        "This category has more than 1000 items. Results may be incomplete."
                                    )

                                if products:
                                    sorted_products = process_products(
                                        products, include_price
                                    )
                                    if sorted_products:
                                        st.success(
                                            f"Found {len(sorted_products)} products."
                                        )

                                        # Apply custom CSS to control image size
                                        st.markdown(
                                            """
                                            <style>
                                            .product-image {
                                                width: 150px;
                                                height: 150px;
                                                object-fit: contain;
                                                display: block;
                                                margin-left: auto;
                                                margin-right: auto;
                                            }
                                            </style>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        for product in sorted_products:
                                            with st.container():
                                                col1, col2 = st.columns([1, 3])
                                                with col1:
                                                    image_url = product[
                                                        "imageUrlTemplates"
                                                    ][0].replace(
                                                        "{transformations}",
                                                        "f_auto,q_auto,c_fit,h_440,w_440",
                                                    )
                                                    st.markdown(
                                                        f'<img src="{image_url}" alt="{product["name"]}" class="product-image">',
                                                        unsafe_allow_html=True,
                                                    )
                                                with col2:
                                                    st.markdown(
                                                        f"### {product['name']}"
                                                    )
                                                    st.markdown(
                                                        f"**Brand:** {product['brandName']}"
                                                    )
                                                    st.markdown(
                                                        f"**Rating:** {product.get('ratingValue', 'N/A')} (based on {product.get('ratingCount', 'N/A')} ratings)"
                                                    )
                                                    st.markdown(
                                                        f"**Price:** {product['price']['formattedValue']}"
                                                    )
                                                    st.markdown(
                                                        f"**Popularity Score:** {product['popularity_score']}"
                                                    )
                                                    st.markdown(
                                                        f"[View Product](https://www.mojadm.sk{product['relativeProductUrl']})"
                                                    )
                                                    st.write("---")
                                    else:
                                        st.warning(
                                            "No products with reviews found for this category."
                                        )
                                else:
                                    st.warning("No products found for this category.")
                            else:
                                st.error(
                                    "Failed to fetch data. Please check the category ID and try again."
                                )
                    else:
                        st.warning("No filters found for this category.")


if __name__ == "__main__":
    main()
