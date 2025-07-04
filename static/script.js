// static/script.js

// --- Code Sidebar (inchangé) ---
const sidebar = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
const toggleSidebarMobileButton = document.getElementById('toggleSidebarMobile');

if (sidebar && toggleSidebarMobileButton && sidebarBackdrop) {
    const toggleSidebar = () => {
        sidebar.classList.toggle('hidden');
        sidebarBackdrop.classList.toggle('hidden');
    };

    toggleSidebarMobileButton.addEventListener('click', toggleSidebar);
    sidebarBackdrop.addEventListener('click', toggleSidebar);
}

// --- Code pour faire disparaître les messages flash (inchangé) ---
document.addEventListener('DOMContentLoaded', () => {
    const alertElements = document.querySelectorAll('.alert');

    alertElements.forEach(alert => {
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000);
    });


    // --- Code pour gérer le flux de la page d'analyse ---
    const uploadSection = document.getElementById('upload-section');
    const imagePreviewSection = document.getElementById('image-preview-section');
    const resultatsSection = document.getElementById('resultats-section');
    const patientInfoFormSection = document.getElementById('patient-info-form-section');
    const imageUploadInput = document.getElementById('image_upload');
    const imagePreviewElement = document.getElementById('image-preview');
    const uploadButton = document.getElementById('upload-button');
    const analyseButton = document.getElementById('analyse-button');
    const saveButton = document.getElementById('save-button'); // Bouton "Sauvegarder les résultats" (hors formulaire patient)
    const saveFormButton = document.getElementById('save-form-button'); // Bouton "Confirmer et Sauvegarder" (dans formulaire patient)
    const uploadForm = document.getElementById('upload-form');
    const loadingIndicator = document.getElementById('loading-indicator');


    // --- Écouteur d'événement sur le bouton "Télécharger l'image" (inchangé) ---
    uploadButton.addEventListener('click', (event) => {
        event.preventDefault();
        imageUploadInput.click();
    });

    // --- Écouteur d'événement sur le changement de l'input type="file" (image_upload) ---
    imageUploadInput.addEventListener('change', () => {
        const file = imageUploadInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreviewElement.src = e.target.result;
                uploadSection.classList.add('hidden');
                imagePreviewSection.classList.remove('hidden');
                analyseButton.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        } else {
            // Si aucun fichier sélectionné, on réaffiche la section d'upload et on cache la preview
            uploadSection.classList.remove('hidden');
            imagePreviewSection.classList.add('hidden');
            analyseButton.classList.add('hidden');
        }
    });


    // --- Écouteur d'événement sur le bouton "Analyser l'image" (corrigé) ---
    analyseButton.addEventListener('click', (e) => {
        if (!imagePreviewElement.src || imagePreviewElement.src === '#') {
            e.preventDefault();
            alert("Veuillez d'abord sélectionner une image.");
            return;
        }
        imagePreviewSection.classList.add('hidden');
        loadingIndicator.classList.remove('hidden');
        uploadForm.submit();
    });

    // --- Écouteur d'événement sur le bouton "Sauvegarder les résultats" (MODIFIÉ) ---
    saveButton.addEventListener('click', () => {
        console.log("Bouton 'Sauvegarder les résultats' cliqué!");
        patientInfoFormSection.classList.remove('hidden'); // Affiche le formulaire patient
        saveButton.classList.add('hidden'); // Cache le bouton "Sauvegarder les résultats" lui-même
    });

    // --- Cacher initialement la section des infos patient et le bouton "Sauvegarder" (MODIFIÉ) ---
    patientInfoFormSection.classList.add('hidden');
    if (saveButton) { // Vérification pour éviter les erreurs si le bouton n'est pas rendu initialement
        saveButton.classList.add('hidden'); // Cache initialement le bouton "Sauvegarder les résultats"
    }


    // --- Afficher le bouton "Sauvegarder" seulement s'il y a des résultats d'analyse (MODIFIÉ) ---
    if (resultatsSection) {
        if (resultatsSection.children.length > 0) { // Vérifie si la section des résultats a du contenu (résultats affichés)
            saveButton.classList.remove('hidden'); // Affiche le bouton "Sauvegarder" seulement SI des résultats sont affichés

            // --- AJOUT IMPORTANT : Cacher définitivement les sections de téléchargement et prévisualisation ---
            uploadSection.classList.add('hidden');
            imagePreviewSection.classList.add('hidden');
        } else {
            saveButton.classList.add('hidden'); // S'assure que le bouton est caché s'il n'y a pas de résultats
        }
    }

    // --- AJOUT : Cacher les sections upload et preview au chargement de la page SI resultat_analyse existe déjà ---
    if (resultatsSection && resultatsSection.children.length > 0) {
        uploadSection.classList.add('hidden');
        imagePreviewSection.classList.add('hidden');
    }


    const detailButtons = document.querySelectorAll('.detail-button');

    detailButtons.forEach(button => {
        button.addEventListener('click', async (event) => {
            const analyseId = button.dataset.analyseId;
            const modal = document.getElementById(`analyse-detail-modal-${analyseId}`);
            const patientNameSpan = document.getElementById(`modal-patient-name-${analyseId}`);
            const patientDateNaissanceSpan = document.getElementById(`modal-patient-date-naissance-${analyseId}`);
            const analyseDateSpan = document.getElementById(`modal-analyse-date-${analyseId}`);
            const testResultSpan = document.getElementById(`modal-test-result-${analyseId}`);
            const anomalieTypeSpan = document.getElementById(`modal-anomalie-type-${analyseId}`);
            const recommandationSpan = document.getElementById(`modal-recommandation-${analyseId}`);
            const analyseImage = document.getElementById(`modal-analyse-image-${analyseId}`);


            try {
                const response = await fetch(`/analyse_details/${analyseId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();

                patientNameSpan.textContent = `${data.patient_nom} ${data.patient_prenom}`;
                patientDateNaissanceSpan.textContent = data.patient_date_naissance || 'Non renseignée'; // Gérer si date de naissance est null
                analyseDateSpan.textContent = new Date(data.date_analyse).toLocaleDateString('fr-FR', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                testResultSpan.textContent = data.test_positif ? 'Positif' : 'Négatif';
                anomalieTypeSpan.textContent = data.type_anomalie || 'N/A (Test négatif)'; // Gérer si pas d'anomalie
                recommandationSpan.textContent = data.recommandation || 'N/A'; // Gérer si pas de recommandation
                analyseImage.src = `/static/uploaded_images/${data.image_filename}`; // Assurez-vous que le chemin est correct

                // Show modal (using Flowbite's method - adjust if you're not using Flowbite)
                modal.classList.remove('hidden');
                modal.setAttribute('aria-modal', 'true');
                modal.setAttribute('role', 'dialog');

            } catch (error) {
                console.error("Erreur lors de la récupération des détails de l'analyse:", error);
                alert("Erreur lors du chargement des détails de l'analyse. Veuillez réessayer.");
            }
        });
    });
});