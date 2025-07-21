import React from 'react';
import { useNavigate } from 'react-router-dom';

// Import images from src/assets/images
import SS1 from '../assets/images/SS1.jpg';
import img5061 from '../assets/images/5061.png';
import img5062 from '../assets/images/5062.png';
import img5064 from '../assets/images/5064.png';
import img5065 from '../assets/images/5065.png';
import img5066 from '../assets/images/5066.png';
import img5067 from '../assets/images/5067.png';
import img5068 from '../assets/images/5068.png';
import img5069 from '../assets/images/5069.png';
import img5070 from '../assets/images/5070.png';

const Documentation = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="w-full px-8 py-6">
          <div className="max-w-6xl mx-auto">
            <button 
              onClick={() => navigate('/dashboard/settings')} 
              className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-6 transition-colors group"
            >
              <svg className="w-5 h-5 mr-2 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7"/>
              </svg>
              <span className="font-medium">Back to Settings</span>
            </button>
            <div className="text-center">
              <h1 className="text-4xl font-bold text-gray-900 mb-3">
                Twitter API Setup Guide
              </h1>
              <p className="text-gray-600 text-xl">
                Quick 5-minute setup to get your API credentials
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="w-full px-8 py-8">
        <div className="max-w-6xl mx-auto space-y-12">
          
          {/* Step 1: Get Started */}
          <section className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div className="bg-sky-400 px-8 py-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Step 1: Get Started</h2>
                <p className="text-white text-lg">Begin your Twitter API setup journey</p>
              </div>
            </div>
            
            <div className="p-8 space-y-8">
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <h4 className="text-lg font-bold text-gray-900">Quick Setup - Just 5 minutes!</h4>
                </div>
                <p className="text-gray-800 text-base mb-4">
                  <strong>Note:</strong> Please make sure you're logged into Twitter on this browser before starting.
                </p>
                <div className="space-y-3">
                  <p className="text-gray-800 text-base font-medium">1. Click on get started, you will see this screen as below, and there click on "Sign up for free Account":</p>
                  <a 
                    href="https://developer.x.com/en/portal/petition/essential/basic-info" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-block bg-sky-400 hover:bg-sky-500 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
                  >
                    Get Started
                  </a>
                </div>
              </div>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={SS1} 
                    alt="Twitter Developer Portal Sign Up Page" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking "Sign up for free Account", you will see the application form:</p>
            </div>
          </section>

          {/* Step 2: Fill the Form */}
          <section className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div className="bg-sky-400 px-8 py-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Step 2: Fill the Form</h2>
                <p className="text-white text-lg">Complete your application details</p>
              </div>
            </div>
            
            <div className="p-8 space-y-8">
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking on "Sign up for free Account", you will see this screen:</p>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-4">What to do on this page:</p>
                <div className="space-y-3 text-base">
                  <p className="text-gray-800">1. Check all the boxes that apply to you</p>
                  <p className="text-gray-800">2. In the text area, you can paste this example text (or write your own):</p>
                  <div className="bg-white border border-gray-300 rounded-lg p-4 mt-3">
                    <p className="text-gray-700 text-base italic leading-relaxed">
                      "I am planning to use the API for my account growth and engagement automation. This will help me better connect with my audience, schedule content, and analyze engagement patterns to improve my social media presence and reach."
                    </p>
                  </div>
                  <p className="text-gray-800">3. Click "Submit"</p>
                </div>
              </div>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5061} 
                    alt="Twitter Developer Application Form" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After submitting, you will see the dashboard:</p>
            </div>
          </section>

          {/* Step 3: Navigate to Projects */}
          <section className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div className="bg-sky-400 px-8 py-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Step 3: Navigate to Projects</h2>
                <p className="text-white text-lg">Access your default project</p>
              </div>
            </div>
            
            <div className="p-8 space-y-8">
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking submit on the previous screen you will reach here.</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5062} 
                    alt="Twitter Developer Dashboard" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-2">Here, Click "Projects and Apps" from the left sidebar</p>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking, you will see the projects menu:</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5064} 
                    alt="Projects and Apps Menu" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-2">Click on the number below "Default Project"</p>
                <p className="text-gray-800 text-base">Don't click "Default Project" itself - click the number below it!</p>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking the number, you will see the project page:</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5065} 
                    alt="Project Details Screen" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Step 4: Generate Keys */}
          <section className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div className="bg-sky-400 px-8 py-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Step 4: Generate API Keys</h2>
                <p className="text-white text-lg">Create your authentication credentials</p>
              </div>
            </div>
            
            <div className="p-8 space-y-8">
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-2">Click "Keys and Tokens" from this screen</p>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking, you will see the keys page:</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5066} 
                    alt="Keys and Tokens Screen" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-4">Generate your credentials:</p>
                <div className="space-y-3 text-base">
                  <p className="text-gray-800">1. Click "Regenerate" for API Key & Secret</p>
                  <p className="text-gray-800">2. Click "Generate" for Access Token & Secret</p>
                  <p className="text-gray-800 text-lg font-bold">Copy these 4 values: API Key, API Key Secret, Access Token, Access Token Secret</p>
                </div>
              </div>
            </div>
          </section>

          {/* Step 5: Final Setup */}
          <section className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div className="bg-sky-400 px-8 py-6">
              <div>
                <h2 className="text-2xl font-bold text-white">Step 5: Final Setup</h2>
                <p className="text-white text-lg">Configure authentication settings</p>
              </div>
            </div>
            
            <div className="p-8 space-y-8">
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-2">Almost done! Click "Settings" (next to Keys and Tokens)</p>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking Settings, you will see:</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5067} 
                    alt="Project Overview Screen" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-2">Click "Set up" under User authentication settings</p>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">After clicking Set up, you will see:</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5068} 
                    alt="App Settings Screen" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5069} 
                    alt="Authentication Setup Screen" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <p className="text-gray-800 text-lg font-bold mb-4">Configure these settings:</p>
                <div className="space-y-3 text-base">
                  <p className="text-gray-800">1. Select "Read and Write" for permissions</p>
                  <p className="text-gray-800">2. Select "Web App" for type</p>
                  <p className="text-gray-800">3. Scroll down to enter URLs</p>
                </div>
              </div>
              
              <p className="text-gray-700 text-lg leading-relaxed text-center">Scroll down to see the URL fields:</p>
              
              <div className="flex justify-center">
                <div className="border border-gray-200 rounded-xl overflow-hidden shadow-md max-w-4xl">
                  <img 
                    src={img5070} 
                    alt="Callback URL Configuration" 
                    className="w-full h-auto"
                  />
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
                <div className="space-y-4 text-base">
                  <div>
                    <p className="text-gray-800 font-bold text-lg mb-2">Callback URI:</p>
                    <code className="bg-gray-800 text-white px-4 py-2 rounded-lg text-base block">
                      https://twitter-growth-agent-1.onrender.com/twitter/callback
                    </code>
                  </div>
                  <div>
                    <p className="text-gray-800 font-bold text-lg mb-2">Website URL:</p>
                    <code className="bg-gray-800 text-white px-4 py-2 rounded-lg text-base block">
                      https://twitter-growth-agent-1.onrender.com
                    </code>
                  </div>
                  <p className="text-gray-800 text-lg font-bold">4. Click "Save"</p>
                </div>
              </div>
              
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-8 text-center">
                <p className="text-gray-800 text-xl font-bold mb-4">Congratulations! Setup Complete!</p>
                <p className="text-gray-700 text-lg">You can now close this guide and paste your credentials into the settings form.</p>
                <button
                  onClick={() => navigate('/dashboard/settings')}
                  className="mt-6 bg-sky-400 hover:bg-sky-500 text-white font-bold py-3 px-6 rounded-lg text-lg transition-colors"
                >
                  Go to Settings
                </button>
              </div>
            </div>
          </section>

        </div>
      </div>
      
      {/* Footer */}
      <div className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-6xl mx-auto px-8 py-8">
          <div className="text-center">
            <p className="text-gray-600 text-base">
              Need help? Contact support or revisit any step above.
            </p>
            <button
              onClick={() => navigate('/dashboard/settings')}
              className="mt-4 bg-sky-400 hover:bg-sky-500 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Back to Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Documentation;
