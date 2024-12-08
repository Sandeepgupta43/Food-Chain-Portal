fetch(`/search_suggestions?q=${query}`)
    .then(response => response.json())
    .then(data => {
        console.log(data);  // Log the response from the backend
        let suggestionsBox = document.getElementById('suggestions-box');
        suggestionsBox.innerHTML = '';
        data.suggestions.forEach(suggestion => {
            const suggestionItem = document.createElement('div');
            suggestionItem.classList.add('suggestion-item');
            suggestionItem.innerText = suggestion.name;
            suggestionItem.onclick = () => performSearch(suggestion.name);
            suggestionsBox.appendChild(suggestionItem);
        });
    });


// Function to fetch search suggestions
    function fetchSuggestions() {
        const query = document.getElementById('search-input').value;

        if (query.length >= 3) { // Start searching after 3 characters
            fetch(`/search_suggestions?q=${query}`)
                .then(response => response.json())
                .then(data => {
                    let suggestionsBox = document.getElementById('suggestions-box');
                    suggestionsBox.innerHTML = '';
                    data.suggestions.forEach(suggestion => {
                        const suggestionItem = document.createElement('div');
                        suggestionItem.classList.add('suggestion-item');
                        suggestionItem.innerText = suggestion.name;
                        suggestionItem.onclick = () => performSearch(suggestion.name); // On click of suggestion
                        suggestionsBox.appendChild(suggestionItem);
                    });
                });
        }
    }

    // Perform search on enter or after selecting a suggestion
    function performSearch(query = null) {
        const searchQuery = query || document.getElementById('search-input').value;
        if (searchQuery.length > 0) {
            fetch(`/search_results?q=${searchQuery}`)
                .then(response => response.json())
                .then(data => {
                    let resultsContainer = document.getElementById('search-results');
                    resultsContainer.innerHTML = '';
                    data.results.forEach(result => {
                        const resultCard = document.createElement('div');
                        resultCard.classList.add('result-card');
                        resultCard.innerHTML = `
                            <h3>${result.name}</h3>
                            <p>₹${result.price}</p>
                            <button onclick="addToCart(${result.id})">Add to Cart</button>
                        `;
                        resultsContainer.appendChild(resultCard);
                    });
                });
        }
    }