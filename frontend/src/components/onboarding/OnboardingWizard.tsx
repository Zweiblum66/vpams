import React, { useState, useEffect } from 'react';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  Paper,
  LinearProgress,
  Card,
  CardContent,
  IconButton,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  NavigateNext,
  NavigateBefore,
  Check,
  Skip,
  Replay,
  Close,
  PlayCircleOutline,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '../../hooks/redux';
import { 
  startOnboardingFlow,
  completeStep,
  skipStep,
  fetchFlowDetails,
  selectCurrentFlow,
  selectCurrentStep,
  selectFlowProgress,
} from '../../store/slices/onboardingSlice';
import StepContent from './StepContent';
import ProgressIndicator from './ProgressIndicator';
import CompletionCelebration from './CompletionCelebration';

interface OnboardingWizardProps {
  flowId: string;
  onComplete?: () => void;
  onSkip?: () => void;
}

const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  flowId,
  onComplete,
  onSkip,
}) => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  
  const currentFlow = useAppSelector(selectCurrentFlow);
  const currentStep = useAppSelector(selectCurrentStep);
  const flowProgress = useAppSelector(selectFlowProgress);
  
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [stepData, setStepData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSkipDialog, setShowSkipDialog] = useState(false);
  const [skipReason, setSkipReason] = useState('');
  const [showCompletion, setShowCompletion] = useState(false);

  useEffect(() => {
    loadFlow();
  }, [flowId]);

  const loadFlow = async () => {
    try {
      setLoading(true);
      await dispatch(fetchFlowDetails(flowId)).unwrap();
      await dispatch(startOnboardingFlow({ flowId })).unwrap();
    } catch (err) {
      setError('Failed to load onboarding flow');
    } finally {
      setLoading(false);
    }
  };

  const handleNext = async () => {
    if (!currentStep) return;

    try {
      // Validate current step data if needed
      const isValid = validateStepData(currentStep, stepData[currentStep.id]);
      
      if (!isValid) {
        setError('Please complete all required fields');
        return;
      }

      // Complete current step
      await dispatch(completeStep({
        stepId: currentStep.id,
        responseData: stepData[currentStep.id] || {},
        timeSpentSeconds: calculateTimeSpent(),
      })).unwrap();

      // Move to next step or complete flow
      if (activeStepIndex < currentFlow.steps.length - 1) {
        setActiveStepIndex(activeStepIndex + 1);
      } else {
        handleFlowComplete();
      }
    } catch (err) {
      setError('Failed to complete step');
    }
  };

  const handleBack = () => {
    setActiveStepIndex(Math.max(0, activeStepIndex - 1));
  };

  const handleSkip = async () => {
    if (!currentStep || !currentStep.isOptional) return;

    try {
      await dispatch(skipStep({
        stepId: currentStep.id,
        reason: skipReason,
      })).unwrap();

      setShowSkipDialog(false);
      setSkipReason('');

      if (activeStepIndex < currentFlow.steps.length - 1) {
        setActiveStepIndex(activeStepIndex + 1);
      } else {
        handleFlowComplete();
      }
    } catch (err) {
      setError('Failed to skip step');
    }
  };

  const handleFlowComplete = () => {
    setShowCompletion(true);
    setTimeout(() => {
      if (onComplete) {
        onComplete();
      } else {
        navigate('/dashboard');
      }
    }, 3000);
  };

  const handleStepDataChange = (data: any) => {
    setStepData({
      ...stepData,
      [currentStep.id]: data,
    });
  };

  const validateStepData = (step: any, data: any): boolean => {
    if (!step.requiresCompletion) return true;
    
    // Implement validation based on step.validationRules
    if (step.validationRules && step.validationRules.length > 0) {
      // Custom validation logic here
      return true;
    }
    
    return true;
  };

  const calculateTimeSpent = (): number => {
    // Calculate time spent on current step
    // This would track actual time in production
    return 60; // Placeholder
  };

  const handleRestart = async () => {
    try {
      setActiveStepIndex(0);
      setStepData({});
      await dispatch(startOnboardingFlow({ flowId })).unwrap();
    } catch (err) {
      setError('Failed to restart flow');
    }
  };

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 4 }}>
        <LinearProgress />
        <Typography align="center" sx={{ mt: 2 }}>
          Loading onboarding flow...
        </Typography>
      </Box>
    );
  }

  if (showCompletion) {
    return <CompletionCelebration flowName={currentFlow?.name} />;
  }

  if (!currentFlow || !currentStep) {
    return (
      <Alert severity="error">
        Failed to load onboarding flow
      </Alert>
    );
  }

  return (
    <Box sx={{ width: '100%', maxWidth: 1200, mx: 'auto', p: 3 }}>
      {/* Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4">
            {currentFlow.name}
          </Typography>
          <IconButton onClick={() => onSkip?.()}>
            <Close />
          </IconButton>
        </Box>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {currentFlow.description}
        </Typography>

        <ProgressIndicator
          currentStep={activeStepIndex + 1}
          totalSteps={currentFlow.steps.length}
          completionPercentage={flowProgress?.completionPercentage || 0}
          estimatedTimeRemaining={flowProgress?.estimatedTimeRemaining}
        />
      </Paper>

      {/* Stepper */}
      <Stepper activeStep={activeStepIndex} sx={{ mb: 4 }}>
        {currentFlow.steps.map((step, index) => (
          <Step key={step.id} completed={index < activeStepIndex}>
            <StepLabel
              optional={
                step.isOptional && (
                  <Typography variant="caption">Optional</Typography>
                )
              }
            >
              {step.title}
            </StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Step Content */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" gutterBottom>
            {currentStep.title}
          </Typography>
          
          {currentStep.description && (
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              {currentStep.description}
            </Typography>
          )}

          <StepContent
            step={currentStep}
            data={stepData[currentStep.id] || {}}
            onChange={handleStepDataChange}
          />
        </CardContent>
      </Card>

      {/* Navigation */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          startIcon={<NavigateBefore />}
          onClick={handleBack}
          disabled={activeStepIndex === 0}
        >
          Previous
        </Button>

        <Box sx={{ display: 'flex', gap: 2 }}>
          {currentStep.isOptional && (
            <Button
              startIcon={<Skip />}
              onClick={() => setShowSkipDialog(true)}
              color="secondary"
            >
              Skip
            </Button>
          )}
          
          <Button
            variant="contained"
            endIcon={
              activeStepIndex === currentFlow.steps.length - 1 ? (
                <Check />
              ) : (
                <NavigateNext />
              )
            }
            onClick={handleNext}
          >
            {activeStepIndex === currentFlow.steps.length - 1 ? 'Complete' : 'Next'}
          </Button>
        </Box>
      </Box>

      {/* Skip Dialog */}
      <Dialog open={showSkipDialog} onClose={() => setShowSkipDialog(false)}>
        <DialogTitle>Skip This Step?</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to skip this step? You can always come back to it later.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowSkipDialog(false)}>Cancel</Button>
          <Button onClick={handleSkip} color="primary">
            Skip Step
          </Button>
        </DialogActions>
      </Dialog>

      {/* Error Snackbar */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default OnboardingWizard;