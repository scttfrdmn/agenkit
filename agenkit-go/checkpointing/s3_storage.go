package checkpointing

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
)

// S3Storage implements SharedCheckpointStorage backed by Amazon S3.
//
// Key layout: {prefix}/{sessionID}/{checkpointID}.json
//
// Example:
//
//	storage, err := NewS3Storage(ctx, "my-checkpoints", "agents/", "us-west-2")
//	if err != nil { log.Fatal(err) }
//	_ = storage.Save(ctx, checkpoint)
type S3Storage struct {
	client *s3.Client
	bucket string
	prefix string // without trailing slash
}

// NewS3Storage creates an S3Storage that stores checkpoints under prefix inside bucket.
//
// region may be empty if the SDK can resolve it from the environment.
func NewS3Storage(ctx context.Context, bucket, prefix, region string) (*S3Storage, error) {
	var cfgOpts []func(*config.LoadOptions) error
	if region != "" {
		cfgOpts = append(cfgOpts, config.WithRegion(region))
	}

	cfg, err := config.LoadDefaultConfig(ctx, cfgOpts...)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	client := s3.NewFromConfig(cfg)

	// Normalise prefix: strip leading/trailing slashes.
	prefix = strings.Trim(prefix, "/")

	return &S3Storage{
		client: client,
		bucket: bucket,
		prefix: prefix,
	}, nil
}

// URI returns the canonical s3:// URI for this storage.
func (s *S3Storage) URI() string {
	if s.prefix != "" {
		return fmt.Sprintf("s3://%s/%s", s.bucket, s.prefix)
	}
	return fmt.Sprintf("s3://%s", s.bucket)
}

// Ping verifies that the bucket is accessible.
func (s *S3Storage) Ping(ctx context.Context) error {
	_, err := s.client.HeadBucket(ctx, &s3.HeadBucketInput{
		Bucket: aws.String(s.bucket),
	})
	if err != nil {
		return fmt.Errorf("s3 ping failed: %w", err)
	}
	return nil
}

func (s *S3Storage) objectKey(sessionID, checkpointID string) string {
	if s.prefix != "" {
		return fmt.Sprintf("%s/%s/%s.json", s.prefix, sessionID, checkpointID)
	}
	return fmt.Sprintf("%s/%s.json", sessionID, checkpointID)
}

func (s *S3Storage) sessionPrefix(sessionID string) string {
	if s.prefix != "" {
		return fmt.Sprintf("%s/%s/", s.prefix, sessionID)
	}
	return fmt.Sprintf("%s/", sessionID)
}

// Save serialises and uploads a checkpoint.
func (s *S3Storage) Save(ctx context.Context, cp *Checkpoint) error {
	data, err := json.Marshal(cp)
	if err != nil {
		return fmt.Errorf("failed to serialise checkpoint: %w", err)
	}

	key := s.objectKey(cp.SessionID, cp.CheckpointID)
	_, err = s.client.PutObject(ctx, &s3.PutObjectInput{
		Bucket:      aws.String(s.bucket),
		Key:         aws.String(key),
		Body:        bytes.NewReader(data),
		ContentType: aws.String("application/json"),
	})
	if err != nil {
		return fmt.Errorf("failed to upload checkpoint to S3: %w", err)
	}
	return nil
}

// Load downloads and deserialises a checkpoint by ID.
// Returns nil, nil if the object does not exist.
func (s *S3Storage) Load(ctx context.Context, checkpointID string) (*Checkpoint, error) {
	// We don't know the sessionID so we must search across all session prefixes.
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{
		Bucket: aws.String(s.bucket),
		Prefix: aws.String(s.keyPrefix()),
	})

	suffix := checkpointID + ".json"
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list S3 objects: %w", err)
		}
		for _, obj := range page.Contents {
			if strings.HasSuffix(aws.ToString(obj.Key), suffix) {
				return s.download(ctx, aws.ToString(obj.Key))
			}
		}
	}
	return nil, nil
}

// ListCheckpoints lists all checkpoints for sessionID, most recent first.
func (s *S3Storage) ListCheckpoints(ctx context.Context, sessionID string, limit *int) ([]*Checkpoint, error) {
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{
		Bucket: aws.String(s.bucket),
		Prefix: aws.String(s.sessionPrefix(sessionID)),
	})

	type entry struct {
		key          string
		lastModified int64
	}
	var entries []entry

	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list session checkpoints: %w", err)
		}
		for _, obj := range page.Contents {
			if !strings.HasSuffix(aws.ToString(obj.Key), ".json") {
				continue
			}
			var ts int64
			if obj.LastModified != nil {
				ts = obj.LastModified.UnixNano()
			}
			entries = append(entries, entry{key: aws.ToString(obj.Key), lastModified: ts})
		}
	}

	// Sort by LastModified descending (most recent first).
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].lastModified > entries[j].lastModified
	})

	if limit != nil && len(entries) > *limit {
		entries = entries[:*limit]
	}

	checkpoints := make([]*Checkpoint, 0, len(entries))
	for _, e := range entries {
		cp, err := s.download(ctx, e.key)
		if err != nil || cp == nil {
			continue
		}
		checkpoints = append(checkpoints, cp)
	}
	return checkpoints, nil
}

// GetLatest returns the most recently modified checkpoint for sessionID.
func (s *S3Storage) GetLatest(ctx context.Context, sessionID string) (*Checkpoint, error) {
	one := 1
	cps, err := s.ListCheckpoints(ctx, sessionID, &one)
	if err != nil {
		return nil, err
	}
	if len(cps) == 0 {
		return nil, nil
	}
	return cps[0], nil
}

// Delete removes the S3 object for checkpointID.
// Returns true if the object existed and was deleted.
func (s *S3Storage) Delete(ctx context.Context, checkpointID string) (bool, error) {
	cp, err := s.Load(ctx, checkpointID)
	if err != nil {
		return false, err
	}
	if cp == nil {
		return false, nil
	}
	key := s.objectKey(cp.SessionID, checkpointID)
	_, err = s.client.DeleteObject(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return false, fmt.Errorf("failed to delete S3 object: %w", err)
	}
	return true, nil
}

// DeleteSession removes all checkpoints for sessionID.
func (s *S3Storage) DeleteSession(ctx context.Context, sessionID string) (int, error) {
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{
		Bucket: aws.String(s.bucket),
		Prefix: aws.String(s.sessionPrefix(sessionID)),
	})

	var toDelete []types.ObjectIdentifier
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return 0, fmt.Errorf("failed to list session objects: %w", err)
		}
		for _, obj := range page.Contents {
			toDelete = append(toDelete, types.ObjectIdentifier{Key: obj.Key})
		}
	}

	if len(toDelete) == 0 {
		return 0, nil
	}

	// S3 allows up to 1000 objects per batch delete.
	deleted := 0
	for i := 0; i < len(toDelete); i += 1000 {
		end := i + 1000
		if end > len(toDelete) {
			end = len(toDelete)
		}
		out, err := s.client.DeleteObjects(ctx, &s3.DeleteObjectsInput{
			Bucket: aws.String(s.bucket),
			Delete: &types.Delete{Objects: toDelete[i:end]},
		})
		if err != nil {
			return deleted, fmt.Errorf("failed to batch-delete S3 objects: %w", err)
		}
		deleted += len(out.Deleted)
	}
	return deleted, nil
}

// GetCheckpointHistory follows parent links to build a history chain.
func (s *S3Storage) GetCheckpointHistory(ctx context.Context, checkpointID string, maxDepth int) ([]*Checkpoint, error) {
	var history []*Checkpoint
	currentID := checkpointID
	for i := 0; i < maxDepth; i++ {
		cp, err := s.Load(ctx, currentID)
		if err != nil {
			return nil, err
		}
		if cp == nil {
			break
		}
		history = append(history, cp)
		if cp.ParentCheckpointID == nil {
			break
		}
		currentID = *cp.ParentCheckpointID
	}
	return history, nil
}

// keyPrefix returns the storage-level key prefix used for ListObjectsV2 pagination.
func (s *S3Storage) keyPrefix() string {
	if s.prefix != "" {
		return s.prefix + "/"
	}
	return ""
}

// download fetches and deserialises a checkpoint from a known S3 key.
func (s *S3Storage) download(ctx context.Context, key string) (*Checkpoint, error) {
	out, err := s.client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to download S3 object: %w", err)
	}
	defer func() { _ = out.Body.Close() }()

	data, err := io.ReadAll(out.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read S3 object body: %w", err)
	}

	var cp Checkpoint
	if err := json.Unmarshal(data, &cp); err != nil {
		return nil, fmt.Errorf("failed to deserialise checkpoint: %w", err)
	}
	return &cp, nil
}
