'use client';

import { zodResolver } from "@hookform/resolvers/zod";
import { SubmitHandler, useForm } from "react-hook-form";
import { z } from "zod";
import { APIService } from "./services/api.service";

const formSchema = z.object({
    name: z.string().regex(/^[A-Za-z\s]+$/),
    age: z.number().int().positive().min(13).max(150),
    email: z.string().email(),
    password: z.string().min(8)
  });

type FormValues = z.infer<typeof formSchema>;

export function UploadForm() {
    const {
        register,
        handleSubmit,
        setError,
        formState: { errors, isSubmitting },
      } = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
          name: "",
          age: 18,
          email: "",
          password: ""
        }
      });

      const onSubmit: SubmitHandler<FormValues> = async (data) => {
        try {
          const result = await APIService.upload(data);
          console.log(data);
        } catch (error) {
          setError("root", {
            message: "This email is already taken",
          });
        }
      };

      return (
        <>

            <header className="flex items-center justify-between p-4 bg-white shadow-md">
                <div className="text-2xl font-bold text-gray-800">MyApp</div>
            </header>

            <div className='w-full items-center gap-4 bg-white rounded-lg border'>
                <form className="max-w-md mx-auto p-4 space-y-4" onSubmit={handleSubmit(onSubmit)}>
                    {/* Name Input */}
                    <div>
                        <label className="block mb-1">Name</label>
                        <input
                            {...register("name")}
                            type="text"
                            className="w-full p-2 border rounded"
                            aria-invalid={!!errors.name}
                        />
                        {errors.name && (
                            <p className="text-red-500 text-sm">{errors.name.message}</p>
                        )}
                    </div>

                    {/* Age Input */}
                    <div>
                        <label className="block mb-1">Age</label>
                        <input
                            {...register("age", { valueAsNumber: true })}
                            type="number"
                            className="w-full p-2 border rounded"
                            aria-invalid={!!errors.age}
                        />
                        {errors.age && (
                            <p className="text-red-500 text-sm">{errors.age.message}</p>
                        )}
                    </div>

                    {/* Email Input */}
                    <div>
                        <label className="block mb-1">Email</label>
                        <input
                            {...register("email")}
                            type="email"
                            className="w-full p-2 border rounded"
                            aria-invalid={!!errors.email}
                        />
                        {errors.email && (
                            <p className="text-red-500 text-sm">{errors.email.message}</p>
                        )}
                    </div>

                    {/* Password Input */}
                    <div>
                        <label className="block mb-1">Password</label>
                        <input
                            {...register("password")}
                            type="password"
                            className="w-full p-2 border rounded"
                            aria-invalid={!!errors.password}
                        />
                        {errors.password && (
                            <p className="text-red-500 text-sm">{errors.password.message}</p>
                        )}
                    </div>

                    {/* Submit Button */}
                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
                    >
                        {isSubmitting ? "Submitting..." : "Submit"}
                    </button>

                    {/* Root Error */}
                    {errors.root && (
                        <p className="text-red-500 text-center">{errors.root.message}</p>
                    )}
                </form>
            </div>
        </>
    );
}

