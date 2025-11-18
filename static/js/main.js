document.addEventListener('DOMContentLoaded', function() {
    const userForm = document.getElementById('userForm');
    const occupationSelect = document.getElementById('occupation');
    const fieldGroup = document.getElementById('fieldGroup');
    const experienceGroup = document.getElementById('experienceGroup');

    // Show/hide fields based on occupation
    occupationSelect.addEventListener('change', function() {
        const occupation = this.value;
        if (occupation === 'working_professional' || occupation === 'career_changer') {
            fieldGroup.style.display = 'block';
            experienceGroup.style.display = 'block';
        } else if (occupation === 'fresh_graduate') {
            fieldGroup.style.display = 'block';
            experienceGroup.style.display = 'none';
            document.getElementById('experience_years').value = '0';
        } else {
            fieldGroup.style.display = 'none';
            experienceGroup.style.display = 'none';
            document.getElementById('experience_years').value = '0';
        }
    });

    // Update score values for sliders
    // Update score values for sliders - FIXED VERSION
document.querySelectorAll('.score-slider').forEach(slider => {
    // Find the next sibling that is a span with class 'score-value'
    const valueSpan = slider.parentElement.querySelector('.score-value');
    valueSpan.textContent = slider.value;
    
    slider.addEventListener('input', function() {
        valueSpan.textContent = this.value;
    });
});

    userForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(userForm);
        const userInfo = {
            name: formData.get('name'),
            age: parseInt(formData.get('age')),
            occupation: formData.get('occupation'),
            education_level: formData.get('education_level'),
            current_field: formData.get('current_field') || null,
            experience_years: parseInt(formData.get('experience_years') || '0'),
            realistic_score: parseInt(formData.get('realistic_score')),
            investigative_score: parseInt(formData.get('investigative_score')),
            artistic_score: parseInt(formData.get('artistic_score')),
            social_score: parseInt(formData.get('social_score')),
            enterprising_score: parseInt(formData.get('enterprising_score')),
            conventional_score: parseInt(formData.get('conventional_score'))
        };

        try {
            const response = await fetch('/api/user/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userInfo)
            });

            if (response.ok) {
                const data = await response.json();
                window.location.href = '/results';
            } else {
                const errorData = await response.json();
                alert('Error registering user: ' + (errorData.error || 'Please try again.'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
        }
    });
});