export const getCandidates = async () => {
  return [
    {
      id: 1,
      name: "Sarah Johnson",
      email: "sarah@email.com",
      role: "Frontend Developer",
      score: 92,
      status: "Shortlisted",
      skills: "React, TypeScript",
    },
  ];
};

export const uploadResume = async (file: File, jobDesc: string) => {
  const formData = new FormData();
  formData.append("resume", file);
  formData.append("job_description", jobDesc);

  const res = await fetch("http://127.0.0.1:8000/api/upload-resume/", {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error("Failed to analyze resume");
  }

  return res.json();
};