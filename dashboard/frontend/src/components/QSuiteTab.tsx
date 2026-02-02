import React, { useState, useCallback, useRef } from 'react';
import { Zap, Upload, FileText, AlertCircle, CheckCircle, ChevronDown, ChevronUp, Download, Target, BookOpen, Activity, TrendingUp, Shield, Globe, ExternalLink } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

interface WebSearchResult {
  search_performed: boolean;
  trial_name: string;
  key_findings: string[];
  sources: string[];
  accuracy_adjustment: number;
  verification_note: string;
}

interface QBoostAssessment {
  accuracy_score: number;
  accuracy_grade: string;
  accuracy_issues: string[];
  lo_score: number;
  lo_grade: string;
  lo_assessment: string;
  lo_suggestions: string[];
  suggestions: string[];
  model_name?: string;  // For Quorum mode
  web_search?: WebSearchResult;  // Web fact-check results
}

interface QuorumResult {
  gpt_qboost: QBoostAssessment | null;
  claude_qboost: QBoostAssessment | null;
  gemini_qboost: QBoostAssessment | null;
  gpt_qcore_score: number;
  claude_qcore_score: number;
  gemini_qcore_score: number;
  avg_qcore_score: number;
  avg_accuracy_score: number;
  avg_lo_score: number;
}

interface SimilarQuestion {
  question_id: number;
  source_id: string;
  similarity_score: number;
  question_stem_preview: string;
  performance: Record<string, any>;
}

interface QuestionAnalysis {
  question_number: number;
  question_stem: string;
  options: string[];
  correct_answer: string;
  learning_objective: string;
  tags: Record<string, any>;
  // QCore results
  qcore_score: number;
  qcore_grade: string;
  qcore_breakdown: Record<string, any>;
  ready_for_deployment: boolean;
  // QBoost results (optional - single model)
  qboost: QBoostAssessment | null;
  // Quorum results (optional - 3-model aggregation)
  quorum?: QuorumResult;
  is_quorum?: boolean;
  // QPredict results (optional)
  similar_questions: SimilarQuestion[];
  // Metadata
  cme_level: string;
  tagging_model: string;
}

interface AnalysisResult {
  filename: string;
  activity_title: string;
  analysis_timestamp: string;
  total_questions: number;
  avg_qcore_score: number;
  avg_qboost_accuracy: number;
  avg_qboost_lo: number;
  grade_distribution: Record<string, number>;
  ready_count: number;
  ready_percentage: number;
  warnings: string[];
  options_used: {
    qcore: boolean;
    qboost: boolean;
    qpredict: boolean;
  };
  total_cost: number;
  model_used: string;
  questions: QuestionAnalysis[];
}

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 border-green-200',
  B: 'bg-blue-100 text-blue-800 border-blue-200',
  C: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  D: 'bg-orange-100 text-orange-800 border-orange-200',  // D is now the floor (no F)
  'N/A': 'bg-gray-100 text-gray-600 border-gray-200',
};

const GRADE_BG_COLORS: Record<string, string> = {
  A: 'bg-green-500',
  B: 'bg-blue-500',
  C: 'bg-yellow-500',
  D: 'bg-orange-500',  // D is now the floor (no F)
};

// Helper to find web_search result from single-model or Quorum mode
const getWebSearchResult = (q: QuestionAnalysis): WebSearchResult | null => {
  // Check single-model qboost first
  if (q.qboost?.web_search?.search_performed) {
    return q.qboost.web_search;
  }
  // Check Quorum mode - look through all 3 models
  if (q.is_quorum && q.quorum) {
    if (q.quorum.gpt_qboost?.web_search?.search_performed) {
      return q.quorum.gpt_qboost.web_search;
    }
    if (q.quorum.claude_qboost?.web_search?.search_performed) {
      return q.quorum.claude_qboost.web_search;
    }
    if (q.quorum.gemini_qboost?.web_search?.search_performed) {
      return q.quorum.gemini_qboost.web_search;
    }
  }
  return null;
};

export default function QSuiteTab() {
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<string>('gpt');
  const [includeQBoost, setIncludeQBoost] = useState(true);
  const [_includeQPredict, _setIncludeQPredict] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [_progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [expandedQuestion, setExpandedQuestion] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.docx')) {
        setError('Please select a .docx file');
        return;
      }
      setFile(selectedFile);
      setError(null);
      setResult(null);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (!droppedFile.name.endsWith('.docx')) {
        setError('Please select a .docx file');
        return;
      }
      setFile(droppedFile);
      setError(null);
      setResult(null);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const pollAnalysisStatus = async (analysisId: string) => {
    let attempts = 0;
    const maxAttempts = 180; // 3 minutes max

    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`${API_BASE}/qsuite/analysis/${analysisId}`);
        const data = await response.json();

        setProgress(data.progress || 0);

        if (data.status === 'completed') {
          setResult(data.result);
          setAnalyzing(false);
          return;
        } else if (data.status === 'failed') {
          setError(data.message || 'Analysis failed');
          setAnalyzing(false);
          return;
        }

        await new Promise(resolve => setTimeout(resolve, 1000));
        attempts++;
      } catch (err) {
        setError('Error checking analysis status');
        setAnalyzing(false);
        return;
      }
    }

    setError('Analysis timed out');
    setAnalyzing(false);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', model);
      formData.append('include_qboost', String(includeQBoost));
      formData.append('include_qpredict', String(_includeQPredict));

      const response = await fetch(`${API_BASE}/qsuite/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploading(false);
      setAnalyzing(true);
      setProgress(10);

      // Poll for results
      await pollAnalysisStatus(data.analysis_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const downloadResults = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qsuite_analysis_${result.filename.replace('.docx', '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Calculate estimated cost per model (fixed costs, not dependent on selection)
  const getModelCost = (modelId: string) => {
    const baseCosts: Record<string, number> = {
      'gpt': 0.015,
      'claude': 0.07,
      'gemini': 0.015,
      'quorum': 0.10,  // All 3 models combined (~$0.50 for 5 questions with web search)
    };
    const baseCost = baseCosts[modelId] || 0.015;
    const multiplier = includeQBoost ? 1 : 0.6; // QCore only is cheaper
    return baseCost * multiplier;
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 text-white p-6 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/20 rounded-lg">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Q-Suite</h1>
            <p className="text-purple-100 text-sm">
              Comprehensive Question Quality Analysis
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {!result ? (
          /* Upload Section */
          <div className="max-w-2xl mx-auto">
            {/* Drop Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => fileInputRef.current?.click()}
              className={`
                border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
                ${file ? 'border-purple-400 bg-purple-50' : 'border-gray-300 hover:border-purple-400 hover:bg-purple-50'}
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx"
                onChange={handleFileSelect}
                className="hidden"
              />

              {file ? (
                <div className="space-y-3">
                  <FileText className="w-16 h-16 mx-auto text-purple-500" />
                  <p className="text-lg font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className="w-16 h-16 mx-auto text-gray-400" />
                  <p className="text-lg font-medium text-gray-700">
                    Drop your outcomes document here
                  </p>
                  <p className="text-sm text-gray-500">
                    or click to browse (.docx files only)
                  </p>
                </div>
              )}
            </div>

            {/* Tool Selection (Checkboxes) */}
            <div className="mt-6 p-4 bg-white rounded-lg border">
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Analysis Tools
              </label>
              <div className="space-y-3">
                {/* QCore - Always enabled */}
                <div className="flex items-center p-3 rounded-lg bg-purple-50 border border-purple-200">
                  <input
                    type="checkbox"
                    checked={true}
                    disabled
                    className="w-4 h-4 text-purple-600 border-gray-300 rounded cursor-not-allowed"
                  />
                  <div className="ml-3 flex-1">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-purple-600" />
                      <span className="font-medium text-gray-900">QCore</span>
                      <span className="text-xs bg-purple-200 text-purple-800 px-2 py-0.5 rounded">Required</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      Quality scoring: flaw detection, structure analysis, deployment readiness
                    </p>
                  </div>
                </div>

                {/* QBoost - Optional */}
                <label className="flex items-center p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    checked={includeQBoost}
                    onChange={(e) => setIncludeQBoost(e.target.checked)}
                    className="w-4 h-4 text-indigo-600 border-gray-300 rounded"
                  />
                  <div className="ml-3 flex-1">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-indigo-600" />
                      <span className="font-medium text-gray-900">QBoost</span>
                      <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">Recommended</span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      LLM accuracy check, learning objective alignment, improvement suggestions
                    </p>
                  </div>
                </label>

                {/* QPredict - Coming Soon (disabled) */}
                <div className="flex items-center p-3 rounded-lg border border-gray-200 bg-gray-50 opacity-60 cursor-not-allowed">
                  <input
                    type="checkbox"
                    checked={false}
                    disabled
                    className="w-4 h-4 text-gray-400 border-gray-300 rounded cursor-not-allowed"
                  />
                  <div className="ml-3 flex-1">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-gray-400" />
                      <span className="font-medium text-gray-500">QPredict</span>
                      <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded">Coming Soon</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Performance prediction: find similar questions, analyze patterns, predict outcomes
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Model Selection */}
            <div className="mt-4 p-4 bg-white rounded-lg border">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Analysis Model
              </label>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { id: 'gpt', name: 'GPT-5.2', tagline: '' },
                  { id: 'claude', name: 'Claude Opus', tagline: '' },
                  { id: 'gemini', name: 'Gemini 2.5', tagline: '' },
                  { id: 'quorum', name: 'Quorum', tagline: '3 LLM aggregator' },
                ].map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setModel(m.id)}
                    className={`
                      p-3 rounded-lg border-2 transition-all text-left
                      ${model === m.id ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'}
                      ${m.id === 'quorum' ? 'bg-gradient-to-br from-purple-50 to-indigo-50' : ''}
                    `}
                  >
                    <div className="font-medium text-gray-900">{m.name}</div>
                    {m.tagline && <div className="text-xs text-purple-600 font-medium">{m.tagline}</div>}
                    <div className="text-xs text-gray-500">~${getModelCost(m.id).toFixed(2)}/q</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <p className="text-red-700">{error}</p>
              </div>
            )}

            {/* Progress Display */}
            {(uploading || analyzing) && (
              <div className="mt-4 p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Activity className="w-5 h-5 text-purple-500" />
                    <span className="absolute -top-1 -right-1 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-purple-500"></span>
                    </span>
                  </div>
                  <span className="text-purple-700 font-medium flex items-center gap-1">
                    {uploading ? (
                      'Uploading document'
                    ) : (
                      <>
                        Analyzing questions
                        <span className="inline-flex w-8">
                          <span className="animate-[ellipsis_1.5s_infinite]">.</span>
                          <span className="animate-[ellipsis_1.5s_infinite_0.3s]">.</span>
                          <span className="animate-[ellipsis_1.5s_infinite_0.6s]">.</span>
                        </span>
                      </>
                    )}
                  </span>
                </div>
                {analyzing && (
                  <p className="text-sm text-purple-600 mt-2 ml-8">
                    {model === 'quorum'
                      ? 'Running GPT, Claude, and Gemini in parallel...'
                      : `Processing with ${model === 'gpt' ? 'GPT-5.2' : model === 'claude' ? 'Claude Opus' : 'Gemini 2.5'}...`}
                  </p>
                )}
                {/* Animated bar instead of percentage */}
                <div className="w-full bg-purple-200 rounded-full h-1.5 mt-3 overflow-hidden">
                  <div className="bg-purple-600 h-1.5 rounded-full animate-[indeterminate_1.5s_infinite_ease-in-out] w-1/3" />
                </div>
              </div>
            )}

            {/* Upload Button */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleUpload}
                disabled={!file || uploading || analyzing}
                className={`
                  flex-1 py-3 px-6 rounded-lg font-medium flex items-center justify-center gap-2 transition-all
                  ${file && !uploading && !analyzing
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-gray-200 text-gray-500 cursor-not-allowed'}
                `}
              >
                <Activity className="w-5 h-5" />
                Analyze Document
              </button>
              {file && (
                <button
                  onClick={handleReset}
                  className="py-3 px-6 rounded-lg font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Instructions */}
            <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="font-medium text-blue-900 mb-2">How Q-Suite Works</h3>
              <ol className="text-sm text-blue-800 space-y-2 list-decimal list-inside">
                <li>Upload your PER Outcomes Questions Review document (.docx)</li>
                <li>Select the tools you want to run (QCore is always included)</li>
                <li>Choose the AI model for analysis:
                  <ul className="ml-4 mt-1 list-disc">
                    <li><strong>GPT-5.2, Claude Opus, Gemini 2.5</strong> - single model analysis</li>
                    <li><strong>Quorum</strong> - runs all 3 models, aggregates tags, shows 3 separate assessments</li>
                  </ul>
                </li>
                <li>QCore calculates quality scores from LLM-generated tags</li>
                <li>QBoost assesses accuracy and learning objective alignment</li>
                <li>Review results and download the comprehensive report</li>
              </ol>
            </div>
          </div>
        ) : (
          /* Results Section */
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-6 gap-4">
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Questions</div>
                <div className="text-2xl font-bold text-gray-900">{result.total_questions}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                  <Zap className="w-3 h-3" /> QCore Avg
                </div>
                <div className="text-2xl font-bold text-purple-600">{result.avg_qcore_score}</div>
              </div>
              {result.options_used?.qboost && (
                <>
                  <div className="bg-white p-4 rounded-lg border shadow-sm">
                    <div className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                      <Shield className="w-3 h-3" /> Accuracy Avg
                    </div>
                    <div className="text-2xl font-bold text-indigo-600">{result.avg_qboost_accuracy || 'N/A'}</div>
                  </div>
                  <div className="bg-white p-4 rounded-lg border shadow-sm">
                    <div className="text-sm text-gray-500 mb-1 flex items-center gap-1">
                      <Target className="w-3 h-3" /> LO Align Avg
                    </div>
                    <div className="text-2xl font-bold text-blue-600">{result.avg_qboost_lo || 'N/A'}</div>
                  </div>
                </>
              )}
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Ready</div>
                <div className="text-2xl font-bold text-green-600">
                  {result.ready_count}/{result.total_questions}
                </div>
              </div>
              <div className="bg-white p-4 rounded-lg border shadow-sm">
                <div className="text-sm text-gray-500 mb-1">Cost</div>
                <div className="text-2xl font-bold text-gray-600">${result.total_cost.toFixed(3)}</div>
              </div>
            </div>

            {/* Tools Used Badge */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Tools used:</span>
              <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded flex items-center gap-1">
                <Zap className="w-3 h-3" /> QCore
              </span>
              {result.options_used?.qboost && (
                <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded flex items-center gap-1">
                  <Shield className="w-3 h-3" /> QBoost
                </span>
              )}
              {result.options_used?.qpredict && (
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> QPredict
                </span>
              )}
              {result.model_used?.toLowerCase().includes('quorum') && (
                <span className="text-xs bg-gradient-to-r from-purple-100 to-indigo-100 text-purple-800 px-2 py-1 rounded flex items-center gap-1 border border-purple-200">
                  <Activity className="w-3 h-3" /> Quorum (3 LLMs)
                </span>
              )}
            </div>

            {/* Grade Distribution */}
            <div className="bg-white p-4 rounded-lg border shadow-sm">
              <h3 className="font-medium text-gray-900 mb-3">QCore Grade Distribution</h3>
              <div className="flex items-end gap-2 h-32">
                {['A', 'B', 'C', 'D'].map((grade) => {  /* No F grade */
                  const count = result.grade_distribution[grade] || 0;
                  const pct = result.total_questions > 0 ? (count / result.total_questions) * 100 : 0;
                  return (
                    <div key={grade} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full flex flex-col items-center justify-end h-20">
                        <span className="text-xs text-gray-500 mb-1">{count}</span>
                        <div
                          className={`w-full rounded-t ${GRADE_BG_COLORS[grade]} transition-all`}
                          style={{ height: `${Math.max(pct, 4)}%` }}
                        />
                      </div>
                      <span className={`text-sm font-bold px-2 py-0.5 rounded ${GRADE_COLORS[grade]}`}>
                        {grade}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={downloadResults}
                className="flex items-center gap-2 py-2 px-4 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all"
              >
                <Download className="w-4 h-4" />
                Download Results
              </button>
              <button
                onClick={handleReset}
                className="py-2 px-4 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-all"
              >
                Analyze Another Document
              </button>
            </div>

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h3 className="font-medium text-yellow-900 mb-2">Parse Warnings</h3>
                <ul className="text-sm text-yellow-800 space-y-1 list-disc list-inside">
                  {result.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Questions Table */}
            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
              <div className="p-4 border-b bg-gray-50">
                <h3 className="font-medium text-gray-900">Question Analysis</h3>
              </div>
              <div className="divide-y">
                {result.questions.map((q) => (
                  <div key={q.question_number} className="hover:bg-gray-50 transition-colors">
                    <div
                      className="p-4 cursor-pointer flex items-center gap-4"
                      onClick={() => setExpandedQuestion(
                        expandedQuestion === q.question_number ? null : q.question_number
                      )}
                    >
                      <div className="w-8 h-8 flex items-center justify-center bg-gray-100 rounded-full text-sm font-bold">
                        {q.question_number}
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 truncate">{q.question_stem}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {q.cme_level} • {q.tags.topic || 'No topic'}
                        </p>
                      </div>

                      {/* QCore Score */}
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-purple-500" />
                        <span className="text-lg font-bold text-gray-900">{q.qcore_score}</span>
                        <span className={`text-sm font-bold px-2 py-0.5 rounded border ${GRADE_COLORS[q.qcore_grade]}`}>
                          {q.qcore_grade}
                        </span>
                      </div>

                      {/* QBoost Scores (if available) */}
                      {q.qboost && (
                        <>
                          <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-indigo-500" />
                            <span className="text-lg font-bold text-gray-900">{q.qboost.accuracy_score}</span>
                            <span className={`text-sm font-bold px-2 py-0.5 rounded border ${GRADE_COLORS[q.qboost.accuracy_grade] || GRADE_COLORS['N/A']}`}>
                              {q.qboost.accuracy_grade}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Target className="w-4 h-4 text-blue-500" />
                            <span className="text-lg font-bold text-gray-900">{q.qboost.lo_score}</span>
                            <span className={`text-sm font-bold px-2 py-0.5 rounded border ${GRADE_COLORS[q.qboost.lo_grade] || GRADE_COLORS['N/A']}`}>
                              {q.qboost.lo_grade}
                            </span>
                          </div>
                        </>
                      )}

                      {/* Web Verified Indicator - works for both single-model and Quorum mode */}
                      {(() => {
                        const webSearch = getWebSearchResult(q);
                        if (!webSearch) return null;
                        return (
                          <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                            webSearch.accuracy_adjustment > 0
                              ? 'bg-green-100 text-green-700'
                              : webSearch.accuracy_adjustment < 0
                              ? 'bg-red-100 text-red-700'
                              : 'bg-blue-100 text-blue-700'
                          }`}>
                            <Globe className="w-3 h-3" />
                            {webSearch.accuracy_adjustment > 0 ? '✓' : webSearch.accuracy_adjustment < 0 ? '⚠' : '○'}
                          </div>
                        );
                      })()}

                      {/* Ready Indicator */}
                      {q.ready_for_deployment ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <AlertCircle className="w-5 h-5 text-orange-500" />
                      )}

                      {expandedQuestion === q.question_number ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>

                    {/* Expanded Details */}
                    {expandedQuestion === q.question_number && (
                      <div className="px-4 pb-4 space-y-4 border-t bg-gray-50">
                        {/* Question Text */}
                        <div className="pt-4">
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Question</h4>
                          <p className="text-sm text-gray-900 whitespace-pre-wrap">{q.question_stem}</p>
                        </div>

                        {/* Answer Options */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Options</h4>
                          <div className="space-y-1">
                            {q.options.map((opt, i) => (
                              <p
                                key={i}
                                className={`text-sm p-2 rounded ${
                                  opt.startsWith(q.correct_answer)
                                    ? 'bg-green-100 text-green-800 font-medium'
                                    : 'text-gray-700'
                                }`}
                              >
                                {opt}
                              </p>
                            ))}
                          </div>
                        </div>

                        {/* Learning Objective & QBoost Assessment */}
                        {q.learning_objective && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                              <BookOpen className="w-4 h-4" />
                              Learning Objective
                            </h4>
                            <p className="text-sm text-gray-700 bg-indigo-50 p-3 rounded">
                              {q.learning_objective}
                            </p>
                            {q.qboost && (
                              <div className="mt-2 p-3 bg-white rounded border">
                                <p className="text-sm text-gray-900">{q.qboost.lo_assessment}</p>
                                {q.qboost.lo_suggestions.length > 0 && (
                                  <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                                    {q.qboost.lo_suggestions.map((s, i) => (
                                      <li key={i}>{s}</li>
                                    ))}
                                  </ul>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* QBoost Accuracy Issues & Suggestions - Single Model */}
                        {!q.is_quorum && q.qboost && (q.qboost.accuracy_issues.length > 0 || q.qboost.suggestions.length > 0) && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                              <Shield className="w-4 h-4" />
                              QBoost Assessment
                            </h4>
                            <div className="p-3 bg-white rounded border space-y-2">
                              {q.qboost.accuracy_issues.length > 0 && (
                                <div>
                                  <span className="text-xs font-medium text-red-600">Accuracy Issues:</span>
                                  <ul className="text-sm text-gray-600 list-disc list-inside">
                                    {q.qboost.accuracy_issues.map((issue, i) => (
                                      <li key={i}>{issue}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                              {q.qboost.suggestions.length > 0 && (
                                <div>
                                  <span className="text-xs font-medium text-blue-600">Improvement Suggestions:</span>
                                  <ul className="text-sm text-gray-600 list-disc list-inside">
                                    {q.qboost.suggestions.map((s, i) => (
                                      <li key={i}>{s}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Web Search Verification Results - works for both single-model and Quorum mode */}
                        {(() => {
                          const webSearch = getWebSearchResult(q);
                          if (!webSearch) return null;
                          return (
                            <div>
                              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                                <Globe className="w-4 h-4" />
                                Web Search Fact-Check
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  webSearch.accuracy_adjustment > 0
                                    ? 'bg-green-100 text-green-700'
                                    : webSearch.accuracy_adjustment < 0
                                    ? 'bg-red-100 text-red-700'
                                    : 'bg-blue-100 text-blue-700'
                                }`}>
                                  {webSearch.accuracy_adjustment > 0 ? 'Verified ✓' : webSearch.accuracy_adjustment < 0 ? 'Concern ⚠' : 'Checked'}
                                </span>
                              </h4>
                              <div className={`p-3 rounded border ${
                                webSearch.accuracy_adjustment > 0
                                  ? 'bg-green-50 border-green-200'
                                  : webSearch.accuracy_adjustment < 0
                                  ? 'bg-red-50 border-red-200'
                                  : 'bg-blue-50 border-blue-200'
                              }`}>
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-xs font-medium text-gray-600">Trial:</span>
                                  <span className="text-sm font-bold">{webSearch.trial_name}</span>
                                  {webSearch.accuracy_adjustment !== 0 && (
                                    <span className={`text-xs ${webSearch.accuracy_adjustment > 0 ? 'text-green-600' : 'text-red-600'}`}>
                                      ({webSearch.accuracy_adjustment > 0 ? '+' : ''}{webSearch.accuracy_adjustment} accuracy)
                                    </span>
                                  )}
                                </div>
                                {webSearch.key_findings.length > 0 && (
                                  <div className="mb-2">
                                    <span className="text-xs font-medium text-gray-600">Key Findings:</span>
                                    <ul className="text-sm text-gray-700 list-disc list-inside mt-1">
                                      {webSearch.key_findings.slice(0, 3).map((finding, i) => (
                                        <li key={i}>{finding}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {webSearch.sources.length > 0 && (
                                  <div className="flex items-center gap-2 text-xs text-gray-500">
                                    <ExternalLink className="w-3 h-3" />
                                    Sources: {webSearch.sources.slice(0, 2).join(', ')}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Quorum Results - 3 Model Assessments */}
                        {q.is_quorum && q.quorum && (
                          <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                              <Shield className="w-4 h-4" />
                              Quorum Assessment (3 LLM Aggregator)
                            </h4>
                            <div className="grid grid-cols-3 gap-3">
                              {/* GPT Assessment */}
                              <div className="p-3 bg-gradient-to-br from-green-50 to-emerald-50 rounded border border-green-200">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-green-800">GPT-5.2</span>
                                  <span className="text-sm font-bold text-green-600">{q.quorum.gpt_qcore_score}</span>
                                </div>
                                {q.quorum.gpt_qboost && (
                                  <div className="space-y-1 text-xs">
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Accuracy:</span>
                                      <span className={`font-medium ${GRADE_COLORS[q.quorum.gpt_qboost.accuracy_grade] || ''}`}>
                                        {q.quorum.gpt_qboost.accuracy_score}
                                      </span>
                                    </div>
                                    {q.quorum.gpt_qboost.suggestions.slice(0, 2).map((s, i) => (
                                      <div key={i} className="text-gray-500 text-xs">• {s}</div>
                                    ))}
                                  </div>
                                )}
                              </div>

                              {/* Claude Assessment */}
                              <div className="p-3 bg-gradient-to-br from-orange-50 to-amber-50 rounded border border-orange-200">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-orange-800">Claude Opus</span>
                                  <span className="text-sm font-bold text-orange-600">{q.quorum.claude_qcore_score}</span>
                                </div>
                                {q.quorum.claude_qboost && (
                                  <div className="space-y-1 text-xs">
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Accuracy:</span>
                                      <span className={`font-medium ${GRADE_COLORS[q.quorum.claude_qboost.accuracy_grade] || ''}`}>
                                        {q.quorum.claude_qboost.accuracy_score}
                                      </span>
                                    </div>
                                    {q.quorum.claude_qboost.suggestions.slice(0, 2).map((s, i) => (
                                      <div key={i} className="text-gray-500 text-xs">• {s}</div>
                                    ))}
                                  </div>
                                )}
                              </div>

                              {/* Gemini Assessment */}
                              <div className="p-3 bg-gradient-to-br from-blue-50 to-indigo-50 rounded border border-blue-200">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-blue-800">Gemini 2.5</span>
                                  <span className="text-sm font-bold text-blue-600">{q.quorum.gemini_qcore_score}</span>
                                </div>
                                {q.quorum.gemini_qboost && (
                                  <div className="space-y-1 text-xs">
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Accuracy:</span>
                                      <span className={`font-medium ${GRADE_COLORS[q.quorum.gemini_qboost.accuracy_grade] || ''}`}>
                                        {q.quorum.gemini_qboost.accuracy_score}
                                      </span>
                                    </div>
                                    {q.quorum.gemini_qboost.suggestions.slice(0, 2).map((s, i) => (
                                      <div key={i} className="text-gray-500 text-xs">• {s}</div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                            <div className="mt-3 pt-3 border-t border-gray-200 grid grid-cols-3 gap-4 text-center text-sm">
                              <div>
                                <span className="text-gray-500">Avg QCore</span>
                                <div className="font-bold text-purple-600">{q.quorum.avg_qcore_score}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Avg Accuracy</span>
                                <div className="font-bold text-indigo-600">{q.quorum.avg_accuracy_score || 'N/A'}</div>
                              </div>
                              <div>
                                <span className="text-gray-500">Avg LO Align</span>
                                <div className="font-bold text-blue-600">{q.quorum.avg_lo_score || 'N/A'}</div>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* QCore Breakdown */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                            <Zap className="w-4 h-4" />
                            QCore Breakdown
                          </h4>
                          <div className="grid grid-cols-3 gap-4 text-sm">
                            {/* Flaws */}
                            <div className="p-3 bg-white rounded border">
                              <div className="font-medium text-red-600 mb-2">Flaw Deductions</div>
                              {Object.entries(q.qcore_breakdown.flaws || {}).map(([key, val]) => (
                                val !== 0 && (
                                  <div key={key} className="flex justify-between text-gray-600">
                                    <span>{key.replace('flaw_', '').replace(/_/g, ' ')}</span>
                                    <span className="font-mono">{val as number}</span>
                                  </div>
                                )
                              ))}
                              {Object.entries(q.qcore_breakdown.flaws || {}).every(([_, v]) => v === 0) && (
                                <div className="text-gray-400">None</div>
                              )}
                            </div>
                            {/* Structure Deductions */}
                            <div className="p-3 bg-white rounded border">
                              <div className="font-medium text-orange-600 mb-2">Structure Deductions</div>
                              {Object.entries(q.qcore_breakdown.structure_deductions || {}).map(([key, val]) => (
                                <div key={key} className="flex justify-between text-gray-600">
                                  <span className="truncate">{key.split(':')[1] || key}</span>
                                  <span className="font-mono">{val as number}</span>
                                </div>
                              ))}
                              {Object.keys(q.qcore_breakdown.structure_deductions || {}).length === 0 && (
                                <div className="text-gray-400">None</div>
                              )}
                            </div>
                            {/* Structure Bonuses */}
                            <div className="p-3 bg-white rounded border">
                              <div className="font-medium text-green-600 mb-2">Structure Bonuses</div>
                              {Object.entries(q.qcore_breakdown.structure_bonuses || {}).map(([key, val]) => (
                                <div key={key} className="flex justify-between text-gray-600">
                                  <span className="truncate">{key.split(':')[1] || key}</span>
                                  <span className="font-mono text-green-600">+{val as number}</span>
                                </div>
                              ))}
                              {Object.keys(q.qcore_breakdown.structure_bonuses || {}).length === 0 && (
                                <div className="text-gray-400">None</div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Tags */}
                        <div>
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Tags</h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(q.tags).filter(([_, v]) => v !== null && v !== false).map(([key, val]) => (
                              <span key={key} className="text-xs bg-gray-200 px-2 py-1 rounded">
                                <span className="text-gray-500">{key}:</span>{' '}
                                <span className="font-medium">{String(val)}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
