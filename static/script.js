
document.addEventListener('DOMContentLoaded', function() {
    const monitorForm = document.getElementById('monitorForm');
    const interactionsDiv = document.getElementById('interactions');
    const stopButton = document.getElementById('stopButton'); // Added

    monitorForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const formData = new FormData(monitorForm);
        const subredditName = formData.get('subredditName');
        const keywords = formData.get('keywords');

        fetch('/monitor', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                subreddit_name: subredditName,
                keywords: keywords
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log(data);
        })
        .catch(error => console.error('Error:', error));
    });

    stopButton.addEventListener('click', function() { // Added
        fetch('/stop_monitoring', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            console.log(data);
        })
        .catch(error => console.error('Error:', error));
    });

    // Function to fetch and display interactions from the database
    function fetchInteractions() {
        fetch('/interactions')
        .then(response => response.json())
        .then(data => {
            interactionsDiv.innerHTML = '';
            data.interactions.forEach(interaction => {
                const interactionDiv = document.createElement('div');
                interactionDiv.classList.add('interaction');

                // Create HTML elements for each interaction
                const postIdElement = document.createElement('p');
                postIdElement.classList.add('post-id');
                postIdElement.textContent = `Post ID: ${interaction.post_id}`;

                const titleElement = document.createElement('p');
                titleElement.classList.add('title');
                titleElement.textContent = interaction.title;

                const contentElement = document.createElement('p');
                contentElement.classList.add('content');
                contentElement.textContent = interaction.content;

                const responseElement = document.createElement('p');
                responseElement.classList.add('response');
                responseElement.textContent = `Response: ${interaction.response}`;

                // Append elements to the interactionDiv
                interactionDiv.appendChild(postIdElement);
                interactionDiv.appendChild(titleElement);
                interactionDiv.appendChild(contentElement);
                interactionDiv.appendChild(responseElement);

                // Append interactionDiv to interactionsDiv
                interactionsDiv.appendChild(interactionDiv);
            });
        })
        .catch(error => console.error('Error:', error));
    }

    // Check if the current page is the interactions page
    if (window.location.pathname === '/interactions') {
        // Fetch interactions when the interactions page loads
        fetchInteractions();
    }
});






