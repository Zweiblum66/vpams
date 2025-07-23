import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { Timeline, TimelineTrack, TimelineClip, TrackGroup } from '../../types';

export const timelineApi = createApi({
  reducerPath: 'timelineApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/v1/timelines',
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as any).auth.token;
      if (token) {
        headers.set('authorization', `Bearer ${token}`);
      }
      return headers;
    },
  }),
  tagTypes: ['Timeline', 'TimelineTrack', 'TimelineClip', 'TrackGroup'],
  endpoints: (builder) => ({
    // Timeline operations
    getTimeline: builder.query<Timeline, string>({
      query: (id) => `/${id}`,
      providesTags: ['Timeline'],
    }),
    
    getTimelines: builder.query<{ data: Timeline[]; total: number }, {
      project_id?: string;
      page?: number;
      limit?: number;
    }>({
      query: ({ project_id, page = 1, limit = 20 }) => ({
        url: '',
        params: { project_id, page, limit },
      }),
      providesTags: ['Timeline'],
    }),
    
    createTimeline: builder.mutation<Timeline, Partial<Timeline>>({
      query: (timeline) => ({
        url: '',
        method: 'POST',
        body: timeline,
      }),
      invalidatesTags: ['Timeline'],
    }),
    
    updateTimeline: builder.mutation<Timeline, { id: string } & Partial<Timeline>>({
      query: ({ id, ...timeline }) => ({
        url: `/${id}`,
        method: 'PUT',
        body: timeline,
      }),
      invalidatesTags: ['Timeline'],
    }),
    
    deleteTimeline: builder.mutation<void, string>({
      query: (id) => ({
        url: `/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Timeline'],
    }),
    
    // Track operations
    getTimelineTracks: builder.query<TimelineTrack[], string>({
      query: (timelineId) => `/${timelineId}/tracks`,
      providesTags: ['TimelineTrack'],
    }),
    
    createTrack: builder.mutation<TimelineTrack, { timelineId: string; track: Partial<TimelineTrack> }>({
      query: ({ timelineId, track }) => ({
        url: `/${timelineId}/tracks`,
        method: 'POST',
        body: track,
      }),
      invalidatesTags: ['TimelineTrack'],
    }),
    
    updateTrack: builder.mutation<TimelineTrack, { 
      timelineId: string; 
      trackId: string; 
      updates: Partial<TimelineTrack> 
    }>({
      query: ({ timelineId, trackId, updates }) => ({
        url: `/${timelineId}/tracks/${trackId}`,
        method: 'PUT',
        body: updates,
      }),
      invalidatesTags: ['TimelineTrack'],
    }),
    
    deleteTrack: builder.mutation<void, { timelineId: string; trackId: string }>({
      query: ({ timelineId, trackId }) => ({
        url: `/${timelineId}/tracks/${trackId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['TimelineTrack'],
    }),
    
    reorderTracks: builder.mutation<void, { 
      timelineId: string; 
      trackOrder: { id: string; order: number }[] 
    }>({
      query: ({ timelineId, trackOrder }) => ({
        url: `/${timelineId}/tracks/reorder`,
        method: 'POST',
        body: { track_order: trackOrder },
      }),
      invalidatesTags: ['TimelineTrack'],
    }),
    
    // Clip operations
    getTimelineClips: builder.query<TimelineClip[], { timelineId: string; trackId?: string }>({
      query: ({ timelineId, trackId }) => ({
        url: `/${timelineId}/clips`,
        params: trackId ? { track_id: trackId } : {},
      }),
      providesTags: ['TimelineClip'],
    }),
    
    createClip: builder.mutation<TimelineClip, { 
      timelineId: string; 
      clip: Partial<TimelineClip> 
    }>({
      query: ({ timelineId, clip }) => ({
        url: `/${timelineId}/clips`,
        method: 'POST',
        body: clip,
      }),
      invalidatesTags: ['TimelineClip'],
    }),
    
    updateClip: builder.mutation<TimelineClip, { 
      timelineId: string; 
      clipId: string; 
      updates: Partial<TimelineClip> 
    }>({
      query: ({ timelineId, clipId, updates }) => ({
        url: `/${timelineId}/clips/${clipId}`,
        method: 'PUT',
        body: updates,
      }),
      invalidatesTags: ['TimelineClip'],
    }),
    
    deleteClip: builder.mutation<void, { timelineId: string; clipId: string }>({
      query: ({ timelineId, clipId }) => ({
        url: `/${timelineId}/clips/${clipId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['TimelineClip'],
    }),
    
    moveClip: builder.mutation<TimelineClip, { 
      timelineId: string; 
      clipId: string; 
      trackId: string; 
      position: number 
    }>({
      query: ({ timelineId, clipId, trackId, position }) => ({
        url: `/${timelineId}/clips/${clipId}/move`,
        method: 'POST',
        body: { track_id: trackId, position },
      }),
      invalidatesTags: ['TimelineClip'],
    }),
    
    // Track groups
    getTrackGroups: builder.query<TrackGroup[], string>({
      query: (timelineId) => `/${timelineId}/groups`,
      providesTags: ['TrackGroup'],
    }),
    
    createTrackGroup: builder.mutation<TrackGroup, { 
      timelineId: string; 
      group: Partial<TrackGroup> 
    }>({
      query: ({ timelineId, group }) => ({
        url: `/${timelineId}/groups`,
        method: 'POST',
        body: group,
      }),
      invalidatesTags: ['TrackGroup'],
    }),
    
    updateTrackGroup: builder.mutation<TrackGroup, { 
      timelineId: string; 
      groupId: string; 
      updates: Partial<TrackGroup> 
    }>({
      query: ({ timelineId, groupId, updates }) => ({
        url: `/${timelineId}/groups/${groupId}`,
        method: 'PUT',
        body: updates,
      }),
      invalidatesTags: ['TrackGroup'],
    }),
    
    deleteTrackGroup: builder.mutation<void, { timelineId: string; groupId: string }>({
      query: ({ timelineId, groupId }) => ({
        url: `/${timelineId}/groups/${groupId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['TrackGroup'],
    }),
    
    // Export operations
    exportTimeline: builder.mutation<Blob, { 
      timelineId: string; 
      format: 'aaf' | 'xml' | 'edl' | 'otio' | 'resolve';
      options?: {
        include_media?: boolean;
        include_effects?: boolean;
        include_audio?: boolean;
        frame_rate?: number;
        resolution?: string;
      };
    }>({
      query: ({ timelineId, format, options = {} }) => ({
        url: `/${timelineId}/export`,
        method: 'POST',
        body: { format, ...options },
        responseHandler: (response) => response.blob(),
      }),
    }),
    
    // Import operations
    importTimeline: builder.mutation<Timeline, { 
      timelineId: string; 
      file: File; 
      format: 'aaf' | 'xml' | 'edl' | 'otio';
      options?: {
        merge_tracks?: boolean;
        preserve_timing?: boolean;
        import_media?: boolean;
      };
    }>({
      query: ({ timelineId, file, format, options = {} }) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('format', format);
        Object.entries(options).forEach(([key, value]) => {
          formData.append(key, String(value));
        });
        
        return {
          url: `/${timelineId}/import`,
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: ['Timeline', 'TimelineTrack', 'TimelineClip'],
    }),
    
    // Timeline templates
    getTimelineTemplates: builder.query<Timeline[], void>({
      query: () => '/templates',
      providesTags: ['Timeline'],
    }),
    
    createTimelineFromTemplate: builder.mutation<Timeline, { 
      templateId: string; 
      name: string; 
      projectId: string 
    }>({
      query: ({ templateId, name, projectId }) => ({
        url: `/templates/${templateId}/create`,
        method: 'POST',
        body: { name, project_id: projectId },
      }),
      invalidatesTags: ['Timeline'],
    }),
    
    // Collaboration
    getTimelineComments: builder.query<Comment[], { timelineId: string; timestamp?: number }>({
      query: ({ timelineId, timestamp }) => ({
        url: `/${timelineId}/comments`,
        params: timestamp ? { timestamp } : {},
      }),
    }),
    
    addTimelineComment: builder.mutation<Comment, { 
      timelineId: string; 
      comment: { text: string; timestamp: number; trackId?: string } 
    }>({
      query: ({ timelineId, comment }) => ({
        url: `/${timelineId}/comments`,
        method: 'POST',
        body: comment,
      }),
    }),
    
    // Playback and preview
    generatePreview: builder.mutation<{ preview_url: string }, { 
      timelineId: string; 
      options?: {
        resolution?: string;
        frame_rate?: number;
        start_time?: number;
        end_time?: number;
      };
    }>({
      query: ({ timelineId, options = {} }) => ({
        url: `/${timelineId}/preview`,
        method: 'POST',
        body: options,
      }),
    }),
    
    // Version control
    getTimelineVersions: builder.query<{ versions: Timeline[]; current: number }, string>({
      query: (timelineId) => `/${timelineId}/versions`,
    }),
    
    createTimelineVersion: builder.mutation<Timeline, { 
      timelineId: string; 
      description?: string 
    }>({
      query: ({ timelineId, description }) => ({
        url: `/${timelineId}/versions`,
        method: 'POST',
        body: { description },
      }),
      invalidatesTags: ['Timeline'],
    }),
    
    restoreTimelineVersion: builder.mutation<Timeline, { 
      timelineId: string; 
      versionId: string 
    }>({
      query: ({ timelineId, versionId }) => ({
        url: `/${timelineId}/versions/${versionId}/restore`,
        method: 'POST',
      }),
      invalidatesTags: ['Timeline', 'TimelineTrack', 'TimelineClip'],
    }),
  }),
});

export const {
  useGetTimelineQuery,
  useGetTimelinesQuery,
  useCreateTimelineMutation,
  useUpdateTimelineMutation,
  useDeleteTimelineMutation,
  
  useGetTimelineTracksQuery,
  useCreateTrackMutation,
  useUpdateTrackMutation,
  useDeleteTrackMutation,
  useReorderTracksMutation,
  
  useGetTimelineClipsQuery,
  useCreateClipMutation,
  useUpdateClipMutation,
  useDeleteClipMutation,
  useMoveClipMutation,
  
  useGetTrackGroupsQuery,
  useCreateTrackGroupMutation,
  useUpdateTrackGroupMutation,
  useDeleteTrackGroupMutation,
  
  useExportTimelineMutation,
  useImportTimelineMutation,
  
  useGetTimelineTemplatesQuery,
  useCreateTimelineFromTemplateMutation,
  
  useGetTimelineCommentsQuery,
  useAddTimelineCommentMutation,
  
  useGeneratePreviewMutation,
  
  useGetTimelineVersionsQuery,
  useCreateTimelineVersionMutation,
  useRestoreTimelineVersionMutation,
} = timelineApi;