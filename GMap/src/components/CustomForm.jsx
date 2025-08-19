import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";

const CustomForm = () => {
  const [direction, setDirection] = useState("");
  const [village, setVillage] = useState("");
  const [surveyNumber, setSurveyNumber] = useState("");
  const [image, setImage] = useState(null);
  const [inputType, setInputType] = useState("survey"); // "survey" or "image"
  
  // Dynamic data from backend
  const [villages, setVillages] = useState([]);
  const [surveyNumbers, setSurveyNumbers] = useState([]);
  const [loadingVillages, setLoadingVillages] = useState(false);
  const [loadingSurveyNumbers, setLoadingSurveyNumbers] = useState(false);

  const directions = ["North", "South"];
  
  // Fetch villages from backend
   useEffect(() => {
     const fetchVillages = async () => {
       setLoadingVillages(true);
       try {
         const response = await fetch('http://localhost:5000/api/villages');
         if (response.ok) {
           const data = await response.json();
           if (data.success) {
             setVillages(data.villages);
           } else {
             throw new Error(data.error);
           }
         } else {
           throw new Error('Failed to fetch villages');
         }
       } catch (error) {
         console.error('Error fetching villages:', error);
         // Fallback to hardcoded values
         setVillages([
           "ambeli", "antorieum", "latambarcem"
         ]);
       } finally {
         setLoadingVillages(false);
       }
     };
     
     fetchVillages();
   }, []);
  
  // Fetch survey numbers when village changes
   useEffect(() => {
     if (village) {
       const fetchSurveyNumbers = async () => {
         setLoadingSurveyNumbers(true);
         setSurveyNumber(''); // Reset survey number when village changes
         try {
           const response = await fetch(`http://localhost:5000/api/village/${village}/survey-numbers`);
           if (response.ok) {
             const data = await response.json();
             if (data.success) {
               setSurveyNumbers(data.survey_numbers);
             } else {
               console.error('Error fetching survey numbers:', data.error);
               setSurveyNumbers([]);
             }
           } else {
             console.error('Failed to fetch survey numbers');
             setSurveyNumbers([]);
           }
         } catch (error) {
           console.error('Error fetching survey numbers:', error);
           setSurveyNumbers([]);
         } finally {
           setLoadingSurveyNumbers(false);
         }
       };
       
       fetchSurveyNumbers();
     } else {
       setSurveyNumbers([]);
       setSurveyNumber('');
     }
   }, [village]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file && file.size > 5 * 1024 * 1024) {
      // 5MB limit
      toast.error("File size should be less than 5MB");
      return;
    }
    setImage(file);
  };

  const generateApplicationId = () => {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 1000);
    return `APP${timestamp}${random}`;
  };

  const handleVillageChange = (e) => {
    setVillage(e.target.value);
    setSurveyNumber(''); // Reset survey number when village changes
    setErrors(prev => ({ ...prev, village: '', surveyNumber: '' })); // Clear related errors
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!direction || !village) {
      toast.error("Please select direction and village");
      return;
    }
    
    if (inputType === "survey" && !surveyNumber) {
      toast.error("Please enter survey number");
      return;
    }
    
    if (inputType === "image" && !image) {
      toast.error("Please upload an image");
      return;
    }
    
    const applicationId = generateApplicationId();
    const applicationData = {
      id: applicationId,
      direction,
      village,
      surveyNumber: inputType === "survey" ? surveyNumber : null,
      image: inputType === "image" ? image : null,
      submissionDate: new Date().toISOString().split('T')[0],
      status: "Pending DSLR Approval",
      type: "Map Comparison Certificate"
    };
    
    // Store in localStorage for demo purposes
    const existingApplications = JSON.parse(localStorage.getItem('mapApplications') || '[]');
    existingApplications.push(applicationData);
    localStorage.setItem('mapApplications', JSON.stringify(existingApplications));
    
    console.log("Application submitted:", applicationData);
    toast.success(`Application submitted successfully! Application ID: ${applicationId}`);
    
    // Reset form
    setDirection("");
    setVillage("");
    setSurveyNumber("");
    setImage(null);
    setInputType("survey");
    setSurveyNumbers([]); // Clear survey numbers
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      className="p-8  rounded-lg max-w-lg mx-auto space-y-6"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <h2 className="text-2xl font-bold text-gray-800">
        Map Comparison Certificate Application
      </h2>

      <div>
        <label className="block text-gray-600 mb-2">Select Direction</label>
        <select
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="">Select Direction...</option>
          {directions.map((dir) => (
            <option key={dir} value={dir}>
              {dir}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-600 mb-2">Select Village</label>
        <select
          value={village}
          onChange={handleVillageChange}
          className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          disabled={loadingVillages}
        >
          <option value="">{loadingVillages ? 'Loading villages...' : 'Select Village...'}</option>
          {villages.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-600 mb-2">Input Method</label>
        <div className="flex space-x-4 mb-4">
          <label className="flex items-center">
            <input
              type="radio"
              value="survey"
              checked={inputType === "survey"}
              onChange={(e) => setInputType(e.target.value)}
              className="mr-2"
            />
            Survey Number
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              value="image"
              checked={inputType === "image"}
              onChange={(e) => setInputType(e.target.value)}
              className="mr-2"
            />
            Image Upload
          </label>
        </div>

        {inputType === "survey" ? (
          surveyNumbers.length > 0 ? (
            <select
              value={surveyNumber}
              onChange={(e) => setSurveyNumber(e.target.value)}
              className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
              disabled={loadingSurveyNumbers}
            >
              <option value="">{loadingSurveyNumbers ? 'Loading survey numbers...' : 'Select Survey Number...'}</option>
              {surveyNumbers.map((feature) => {
                // Create display text for the feature
                let displayText = `Feature ${feature.index}`;
                
                // Add any additional identifying information if available
                const identifiers = ['id', 'plot_id', 'survey_no', 'plot_no', 'number', 'name'];
                for (const key of identifiers) {
                  if (feature[key] && feature[key] !== 'null') {
                    displayText += ` (${key.replace('_', ' ').toUpperCase()}: ${feature[key]})`;
                    break;
                  }
                }
                
                return (
                  <option key={feature.index} value={feature.index}>
                    {displayText}
                  </option>
                );
              })}
            </select>
          ) : (
            <input
              type="text"
              placeholder={loadingSurveyNumbers ? "Loading survey numbers..." : "Enter Feature Index (0-based)"}
              value={surveyNumber}
              onChange={(e) => setSurveyNumber(e.target.value)}
              className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
              disabled={loadingSurveyNumbers}
            />
          )
        ) : (
          <input
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            className="w-full border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        )}
      </div>

      <motion.button
        type="submit"
        className="w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        Submit
      </motion.button>
    </motion.form>
  );
};

export default CustomForm;
