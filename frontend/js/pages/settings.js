function initSettingsPage() {
    console.log("Initializing Settings Page...");
    const languageSelect = document.getElementById('language-select');

    // Load saved language and set the dropdown to the correct value
    const savedLanguage = localStorage.getItem('bovitrack-language') || 'en';
    languageSelect.value = savedLanguage;

    // Listen for changes
    languageSelect.addEventListener('change', handleLanguageChange);
}

function handleLanguageChange(event) {
    const selectedLanguage = event.target.value;
    console.log(`Language changed to: ${selectedLanguage}`);
    
    // THE FIX: Call the correct global function from main-renderer.js
    // This is the designated function to handle all language-switching logic.
    setLanguage(selectedLanguage); 
}